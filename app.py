import streamlit as st
import pandas as pd
import requests
import json
import os

# Configuration
SLEEPER_BASE_URL = "https://api.sleeper.app/v1"
DRAFT_ID = "1255223076447072256"
RANKINGS_FILE = "user_rankings.json"

# User configuration with cool emojis
USER_OPTIONS = {
    'nathan': '🔥 Nathan',
    'nathaniel': '⚡ Nathaniel', 
    'jack': '🚀 Jack',
    'kyle': '💎 Kyle'
}

def save_rankings():
    """Save user rankings to JSON file"""
    try:
        with open(RANKINGS_FILE, 'w') as f:
            json.dump(st.session_state.user_rankings, f, indent=2)
    except Exception as e:
        st.error(f"Error saving rankings: {e}")

def load_rankings():
    """Load user rankings from JSON file"""
    try:
        if os.path.exists(RANKINGS_FILE):
            with open(RANKINGS_FILE, 'r') as f:
                return json.load(f)
        else:
            return {
                'nathan': [],
                'nathaniel': [],
                'jack': [],
                'kyle': []
            }
    except Exception as e:
        st.error(f"Error loading rankings: {e}")
        return {
            'nathan': [],
            'nathaniel': [],
            'jack': [],
            'kyle': []
        }

def load_sleeper_players():
    """Load all NFL players from Sleeper API"""
    try:
        response = requests.get(f"{SLEEPER_BASE_URL}/players/nfl")
        if response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to load players from Sleeper API")
            return {}
    except Exception as e:
        st.error(f"Error connecting to Sleeper API: {e}")
        return {}

def get_draft_picks():
    """Get current draft picks from Sleeper API"""
    try:
        response = requests.get(f"{SLEEPER_BASE_URL}/draft/{DRAFT_ID}/picks")
        if response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to load draft picks")
            return []
    except Exception as e:
        st.error(f"Error getting draft picks: {e}")
        return []

def match_players_to_sleeper(df, sleeper_players, drafted_player_ids):
    """Match FantasyPros players to Sleeper and mark drafted players"""
    df = df.copy()
    df['drafted'] = False
    df['sleeper_id'] = None
    
    # Manual overrides for players that should be marked as drafted
    manual_drafted_players = [
        'Josh Allen'  # Having matching issues, manually mark as drafted
    ]
    
    # Manual mappings for problematic names
    name_mappings = {
        'Josh Allen': ['Josh Allen'],
        'Patrick Mahomes II': ['Patrick Mahomes', 'Patrick Mahomes II'],
        'Brian Thomas Jr.': ['Brian Thomas Jr.', 'Brian Thomas'],
        'Marvin Harrison Jr.': ['Marvin Harrison Jr.', 'Marvin Harrison']
    }
    
    for idx, row in df.iterrows():
        player_name = row['PLAYER NAME'].strip()
        found_match = False
        
        # Check manual drafted overrides first
        if player_name in manual_drafted_players:
            df.at[idx, 'drafted'] = True
            df.at[idx, 'sleeper_id'] = 'manual_override'
            found_match = True
            continue
        
        # Try to find matching Sleeper player
        for sleeper_id, sleeper_player in sleeper_players.items():
            if sleeper_player:
                sleeper_full_name = f"{sleeper_player.get('first_name', '')} {sleeper_player.get('last_name', '')}".strip()
                
                # Check direct name match
                if player_name.lower() == sleeper_full_name.lower():
                    df.at[idx, 'sleeper_id'] = sleeper_id
                    if sleeper_id in drafted_player_ids:
                        df.at[idx, 'drafted'] = True
                    found_match = True
                    break
                
                # Check manual mappings
                if player_name in name_mappings:
                    for alt_name in name_mappings[player_name]:
                        if alt_name.lower() == sleeper_full_name.lower():
                            df.at[idx, 'sleeper_id'] = sleeper_id
                            if sleeper_id in drafted_player_ids:
                                df.at[idx, 'drafted'] = True
                            found_match = True
                            break
                    if found_match:
                        break
                
                # Try partial matching for Jr./II cases
                if not found_match:
                    # Remove suffixes for comparison
                    fantasy_base = player_name.replace(' Jr.', '').replace(' II', '').replace(' III', '').strip().lower()
                    sleeper_base = sleeper_full_name.replace(' Jr.', '').replace(' II', '').replace(' III', '').strip().lower()
                    
                    if fantasy_base == sleeper_base:
                        df.at[idx, 'sleeper_id'] = sleeper_id
                        if sleeper_id in drafted_player_ids:
                            df.at[idx, 'drafted'] = True
                        found_match = True
                        break
    
    return df

def load_players_data():
    """Load players from the FantasyPros CSV file"""
    try:
        df = pd.read_csv('FantasyPros_2025_Dynasty_ALL_Rankings.csv')
        return df
    except Exception as e:
        st.error(f"Error loading players data: {e}")
        return None

def main():
    st.set_page_config(page_title="Dynasty Draft Tool", layout="wide", page_icon="🏈")
    
    # Header
    st.title("🏈 Dynasty Fantasy Football Draft Tool")
    st.markdown("---")
    
    # Initialize session state
    if 'players_data' not in st.session_state:
        st.session_state.players_data = None
    if 'sleeper_players' not in st.session_state:
        st.session_state.sleeper_players = {}
    if 'drafted_players' not in st.session_state:
        st.session_state.drafted_players = set()
    if 'last_draft_refresh' not in st.session_state:
        st.session_state.last_draft_refresh = None
    if 'user_rankings' not in st.session_state:
        st.session_state.user_rankings = load_rankings()
    # Sidebar for user selection
    with st.sidebar:
        st.header("👤 User Selection")
        selected_user = st.selectbox(
            "Choose Your Identity", 
            options=list(USER_OPTIONS.keys()),
            format_func=lambda x: USER_OPTIONS[x],
            index=0
        )
        
        st.markdown("---")
        st.markdown(f"**Selected:** {USER_OPTIONS[selected_user]}")
        
        st.markdown("---")
        st.header("🏈 Draft Status")
        
        # Draft refresh button
        if st.button("🔄 Refresh Draft Data"):
            with st.spinner("Loading draft data..."):
                # Load Sleeper players
                st.session_state.sleeper_players = load_sleeper_players()
                
                # Get draft picks
                picks = get_draft_picks()
                st.session_state.drafted_players = {pick['player_id'] for pick in picks if pick['player_id']}
                
                # Update players data with draft status
                if st.session_state.players_data is not None:
                    st.session_state.players_data = match_players_to_sleeper(
                        st.session_state.players_data, 
                        st.session_state.sleeper_players, 
                        st.session_state.drafted_players
                    )
                
                st.session_state.last_draft_refresh = pd.Timestamp.now()
                st.success(f"✅ Draft refreshed! {len(st.session_state.drafted_players)} players drafted")
        
        # Show draft stats
        if st.session_state.last_draft_refresh:
            st.write(f"**Players Drafted:** {len(st.session_state.drafted_players)}")
            st.write(f"**Last Refresh:** {st.session_state.last_draft_refresh.strftime('%H:%M:%S')}")
        else:
            st.info("Click 'Refresh Draft Data' to load draft status")
    
    # Load the player data
    if st.session_state.players_data is None:
        with st.spinner("Loading FantasyPros Dynasty Rankings..."):
            base_data = load_players_data()
            if base_data is not None:
                # Initialize with no draft data
                base_data['drafted'] = False
                base_data['sleeper_id'] = None
                st.session_state.players_data = base_data
    
    if st.session_state.players_data is None:
        st.error("❌ Could not load player data. Make sure the CSV file is in your repository.")
        st.info("💡 Make sure 'FantasyPros_2025_Dynasty_ALL_Rankings.csv' is in the same folder as your app.py")
        return
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["📊 All Players", "🎯 My Rankings", "👥 Team Consensus"])
    
    with tab1:
        st.header("📊 FantasyPros 2025 Dynasty Rankings")
        
        if st.session_state.players_data is not None:
            # Filter options
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown(f"**Total Players:** {len(st.session_state.players_data)}")
            
            with col2:
                hide_drafted = st.checkbox("🚫 Hide Drafted Players", value=False)
            
            # Filter data based on drafted status
            display_data = st.session_state.players_data.copy()
            
            if hide_drafted:
                display_data = display_data[~display_data['drafted']]
                st.markdown(f"**Showing:** {len(display_data)} available players")
            else:
                drafted_count = display_data['drafted'].sum()
                available_count = len(display_data) - drafted_count
                st.markdown(f"**Available:** {available_count} | **Drafted:** {drafted_count}")
            
            # Prepare display dataframe
            display_df = display_data[['RK', 'TIERS', 'PLAYER NAME', 'TEAM', 'POS', 'AGE', 'BEST', 'WORST', 'AVG.', 'STD.DEV', 'ECR VS. ADP']].copy()
            
            # Format ADP and STD.DEV to 2 decimal places
            if 'AVG.' in display_df.columns:
                display_df['ADP'] = display_df['AVG.'].round(2)
                display_df = display_df.drop('AVG.', axis=1)
            
            if 'STD.DEV' in display_df.columns:
                display_df['STD.DEV'] = display_df['STD.DEV'].round(2)
            
            # Color coding function for drafted players
            def highlight_drafted(row):
                if row.name < len(display_data) and display_data.iloc[row.name]['drafted']:
                    return ['background-color: #ffcccc'] * len(row)  # Light red background
                else:
                    return [''] * len(row)
            
            # Display the dataframe with highlighting
            if not hide_drafted:
                styled_df = display_df.style.apply(highlight_drafted, axis=1)
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    height=600,
                    hide_index=True
                )
            else:
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=600,
                    hide_index=True
                )
            
            # Position stats
            col1, col2, col3, col4 = st.columns(4)
            
            # Extract base position for stats
            base_positions = display_data['POS'].str.extract(r'([A-Z]+)')[0]
            position_counts = base_positions.value_counts()
            
            with col1:
                st.metric("QBs", position_counts.get('QB', 0))
            
            with col2:
                st.metric("RBs", position_counts.get('RB', 0))
            
            with col3:
                st.metric("WRs", position_counts.get('WR', 0))
            
            with col4:
                st.metric("TEs", position_counts.get('TE', 0))
        
        else:
            st.error("❌ Could not load player data. Make sure the CSV file is in your repository.")
            st.info("💡 Make sure 'FantasyPros_2025_Dynasty_ALL_Rankings.csv' is in the same folder as your app.py")
    
    with tab2:
        st.header(f"🎯 {USER_OPTIONS[selected_user]} Rankings")
        
        if st.session_state.players_data is not None:
            # Get available (undrafted) players only
            available_players = st.session_state.players_data[~st.session_state.players_data['drafted']].copy()
            
            if len(available_players) == 0:
                st.info("No available players to rank. Refresh draft data first.")
                return
            
            st.markdown(f"**Available Players to Rank:** {len(available_players)}")
            
            # Get current user's rankings
            current_rankings = st.session_state.user_rankings[selected_user]
            
            # Filter current rankings to only include available players
            valid_rankings = [name for name in current_rankings if name in available_players['PLAYER NAME'].values]
            st.session_state.user_rankings[selected_user] = valid_rankings
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("Your Current Rankings")
                
                if valid_rankings:
                    for i, player_name in enumerate(valid_rankings):
                        player_row = available_players[available_players['PLAYER NAME'] == player_name]
                        if not player_row.empty:
                            player = player_row.iloc[0]
                            
                            rank_col, name_col, btn_col = st.columns([0.5, 3, 1])
                            
                            with rank_col:
                                st.write(f"**{i+1}**")
                            
                            with name_col:
                                st.write(f"{player_name} ({player['POS']} - {player['TEAM']})")
                            
                            with btn_col:
                                if st.button("❌", key=f"remove_{selected_user}_{i}"):
                                    st.session_state.user_rankings[selected_user].remove(player_name)
                                    save_rankings()  # Save after removing
                                    st.rerun()
                            
                            # Move up/down buttons
                            move_col1, move_col2 = st.columns(2)
                            with move_col1:
                                if i > 0 and st.button("⬆️", key=f"up_{selected_user}_{i}"):
                                    rankings = st.session_state.user_rankings[selected_user]
                                    rankings[i], rankings[i-1] = rankings[i-1], rankings[i]
                                    save_rankings()  # Save after reordering
                                    st.rerun()
                            
                            with move_col2:
                                if i < len(valid_rankings) - 1 and st.button("⬇️", key=f"down_{selected_user}_{i}"):
                                    rankings = st.session_state.user_rankings[selected_user]
                                    rankings[i], rankings[i+1] = rankings[i+1], rankings[i]
                                    save_rankings()  # Save after reordering
                                    st.rerun()
                            
                            st.divider()
                else:
                    st.info("No players ranked yet. Add players from the available list →")
            
            with col2:
                st.subheader("Available Players")
                
                # Filter/search options
                search_term = st.text_input("🔍 Search players", placeholder="Enter player name...")
                
                col_pos, col_team = st.columns(2)
                with col_pos:
                    positions = ['All'] + sorted(available_players['POS'].str.extract(r'([A-Z]+)')[0].unique())
                    selected_position = st.selectbox("Position", positions)
                
                with col_team:
                    teams = ['All'] + sorted(available_players['TEAM'].unique())
                    selected_team = st.selectbox("Team", teams)
                
                # Apply filters
                filtered_players = available_players.copy()
                
                if search_term:
                    filtered_players = filtered_players[
                        filtered_players['PLAYER NAME'].str.contains(search_term, case=False, na=False)
                    ]
                
                if selected_position != 'All':
                    filtered_players = filtered_players[
                        filtered_players['POS'].str.contains(selected_position, case=False, na=False)
                    ]
                
                if selected_team != 'All':
                    filtered_players = filtered_players[filtered_players['TEAM'] == selected_team]
                
                # Remove already ranked players
                unranked_players = filtered_players[
                    ~filtered_players['PLAYER NAME'].isin(valid_rankings)
                ]
                
                st.write(f"Showing {len(unranked_players)} unranked players")
                
                # Display available players with add buttons
                for _, player in unranked_players.head(20).iterrows():
                    player_col, add_col = st.columns([4, 1])
                    
                    with player_col:
                        st.write(f"**{player['PLAYER NAME']}**")
                        st.caption(f"{player['POS']} - {player['TEAM']} | ECR: #{player['RK']}")
                    
                    with add_col:
                        if st.button("➕", key=f"add_{selected_user}_{player['PLAYER NAME']}"):
                            st.session_state.user_rankings[selected_user].append(player['PLAYER NAME'])
                            save_rankings()  # Save after adding
                            st.success(f"Added {player['PLAYER NAME']}!")
                            st.rerun()
                    
                    st.divider()
        
        else:
            st.error("❌ Please load player data first from Tab 1")
    
    with tab3:
        st.header("👥 Team Consensus Rankings")
        
        if st.session_state.players_data is not None:
            # Get all ranked players across all users
            all_ranked_players = set()
            for user_rankings in st.session_state.user_rankings.values():
                all_ranked_players.update(user_rankings)
            
            if all_ranked_players:
                consensus_data = []
                
                for player_name in all_ranked_players:
                    # Get player data
                    player_row = st.session_state.players_data[
                        st.session_state.players_data['PLAYER NAME'] == player_name
                    ]
                    
                    if not player_row.empty and not player_row.iloc[0]['drafted']:
                        player = player_row.iloc[0]
                        
                        # Calculate rankings from each user
                        user_ranks = {}
                        rank_values = []
                        
                        for user, rankings in st.session_state.user_rankings.items():
                            if player_name in rankings:
                                rank = rankings.index(player_name) + 1
                                user_ranks[user] = rank
                                rank_values.append(rank)
                            else:
                                user_ranks[user] = None
                        
                        # Calculate average ranking
                        avg_rank = sum(rank_values) / len(rank_values) if rank_values else float('inf')
                        
                        consensus_data.append({
                            'Player': player_name,
                            'Position': player['POS'],
                            'Team': player['TEAM'],
                            'ADP': round(player['AVG.'], 2) if pd.notna(player['AVG.']) else '-',
                            'Avg Rank': f"{avg_rank:.1f}" if avg_rank != float('inf') else '-',
                            '🔥 Nathan': user_ranks['nathan'] or '-',
                            '⚡ Nathaniel': user_ranks['nathaniel'] or '-',
                            '🚀 Jack': user_ranks['jack'] or '-',
                            '💎 Kyle': user_ranks['kyle'] or '-',
                            'Ranked By': f"{len(rank_values)}/4"
                        })
                
                # Sort by average ranking
                consensus_data.sort(key=lambda x: float(x['Avg Rank']) if x['Avg Rank'] != '-' else float('inf'))
                
                if consensus_data:
                    st.markdown(f"**Total Ranked Players:** {len(consensus_data)}")
                    
                    # Convert to dataframe and display
                    df = pd.DataFrame(consensus_data)
                    st.dataframe(df, use_container_width=True, hide_index=True, height=600)
                else:
                    st.info("No consensus data available yet.")
            else:
                st.info("No players have been ranked yet. Start ranking players in Tab 2!")
        
        else:
            st.error("❌ Please load player data first from Tab 1")

if __name__ == "__main__":
    main()