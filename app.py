import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import time

# Configuration
SLEEPER_BASE_URL = "https://api.sleeper.app/v1"

# Initialize session state
if 'user_rankings' not in st.session_state:
    st.session_state.user_rankings = {
        'user1': {},
        'user2': {},
        'user3': {},
        'user4': {}
    }

if 'drafted_players' not in st.session_state:
    st.session_state.drafted_players = set()

if 'all_players' not in st.session_state:
    st.session_state.all_players = {}

# User credentials (in production, use proper authentication)
USER_KEYS = {
    'user1': 'Team Member 1',
    'user2': 'Team Member 2', 
    'user3': 'Team Member 3',
    'user4': 'Team Member 4'
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

def get_draft_info(draft_id):
    """Get draft information from Sleeper API"""
    try:
        response = requests.get(f"{SLEEPER_BASE_URL}/draft/{draft_id}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to load draft information")
            return None
    except Exception as e:
        st.error(f"Error getting draft info: {e}")
        return None

def get_draft_picks(draft_id):
    """Get current draft picks from Sleeper API"""
    try:
        response = requests.get(f"{SLEEPER_BASE_URL}/draft/{draft_id}/picks")
        if response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to load draft picks")
            return []
    except Exception as e:
        st.error(f"Error getting draft picks: {e}")
        return []

def calculate_consensus_ranking(player_id):
    """Calculate consensus ranking for a player across all users"""
    rankings = []
    for user in USER_KEYS.keys():
        if player_id in st.session_state.user_rankings[user]:
            rankings.append(st.session_state.user_rankings[user][player_id])
    
    if rankings:
        return sum(rankings) / len(rankings)
    return float('inf')  # Unranked players go to bottom

def main():
    st.set_page_config(page_title="Dynasty Draft Tool", layout="wide")
    
    st.title("🏈 Dynasty Fantasy Football Draft Tool")
    st.markdown("Collaborative ranking system for your 4-person team")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # User selection
        selected_user = st.selectbox("Select Your User", 
                                   options=list(USER_KEYS.keys()),
                                   format_func=lambda x: USER_KEYS[x])
        
        st.markdown("---")
        
        # Draft ID input
        draft_id = st.text_input("Sleeper Draft ID", 
                                placeholder="Enter your draft ID",
                                help="Find this in your Sleeper draft URL")
        
        if draft_id:
            if st.button("Load Draft Data"):
                with st.spinner("Loading draft data..."):
                    draft_info = get_draft_info(draft_id)
                    if draft_info:
                        st.success("Draft loaded successfully!")
                        st.session_state.draft_info = draft_info
                        
                        # Load current picks
                        picks = get_draft_picks(draft_id)
                        st.session_state.drafted_players = {pick['player_id'] for pick in picks if pick['player_id']}
        
        st.markdown("---")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh draft (30s)", value=False)
        
        if auto_refresh and 'draft_info' in st.session_state:
            time.sleep(30)
            st.rerun()
    
    # Load players if not already loaded
    if not st.session_state.all_players:
        with st.spinner("Loading NFL players..."):
            st.session_state.all_players = load_sleeper_players()
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 My Rankings", "👥 Team Consensus", "📊 Draft Board", "⚙️ Player Database"])
    
    with tab1:
        st.header(f"Rankings for {USER_KEYS[selected_user]}")
        
        # Player search and ranking interface
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Search for players
            search_term = st.text_input("Search Players", placeholder="Enter player name...")
            
            if search_term:
                # Filter players based on search
                matching_players = []
                for player_id, player_data in st.session_state.all_players.items():
                    if player_data and search_term.lower() in f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".lower():
                        matching_players.append((player_id, player_data))
                
                # Display matching players
                for player_id, player_data in matching_players[:10]:  # Limit to top 10
                    if player_id not in st.session_state.drafted_players:
                        col_name, col_pos, col_team, col_rank = st.columns([3, 1, 1, 2])
                        
                        with col_name:
                            st.write(f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}")
                        
                        with col_pos:
                            st.write(player_data.get('position', 'N/A'))
                        
                        with col_team:
                            st.write(player_data.get('team', 'N/A'))
                        
                        with col_rank:
                            current_rank = st.session_state.user_rankings[selected_user].get(player_id, '')
                            new_rank = st.number_input(
                                f"Rank",
                                key=f"rank_{player_id}",
                                value=current_rank if current_rank else 0,
                                min_value=0,
                                max_value=999,
                                step=1
                            )
                            
                            if new_rank > 0:
                                st.session_state.user_rankings[selected_user][player_id] = new_rank
                            elif player_id in st.session_state.user_rankings[selected_user]:
                                del st.session_state.user_rankings[selected_user][player_id]
        
        with col2:
            st.subheader("Your Current Rankings")
            user_rankings = st.session_state.user_rankings[selected_user]
            if user_rankings:
                # Sort by ranking
                sorted_rankings = sorted(user_rankings.items(), key=lambda x: x[1])
                
                for i, (player_id, rank) in enumerate(sorted_rankings):
                    if player_id in st.session_state.all_players:
                        player_data = st.session_state.all_players[player_id]
                        player_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}"
                        status = "❌ DRAFTED" if player_id in st.session_state.drafted_players else "✅ Available"
                        st.write(f"{rank}. {player_name} ({player_data.get('position', 'N/A')}) - {status}")
            else:
                st.info("No rankings yet. Search and rank players above!")
    
    with tab2:
        st.header("Team Consensus Rankings")
        
        # Calculate consensus rankings
        all_ranked_players = set()
        for user_rankings in st.session_state.user_rankings.values():
            all_ranked_players.update(user_rankings.keys())
        
        if all_ranked_players:
            consensus_data = []
            for player_id in all_ranked_players:
                if player_id in st.session_state.all_players:
                    player_data = st.session_state.all_players[player_id]
                    consensus_rank = calculate_consensus_ranking(player_id)
                    
                    # Get individual rankings
                    individual_ranks = {}
                    for user, rankings in st.session_state.user_rankings.items():
                        individual_ranks[user] = rankings.get(player_id, '-')
                    
                    consensus_data.append({
                        'Player': f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}",
                        'Position': player_data.get('position', 'N/A'),
                        'Team': player_data.get('team', 'N/A'),
                        'Consensus': round(consensus_rank, 1) if consensus_rank != float('inf') else '-',
                        'User1': individual_ranks['user1'],
                        'User2': individual_ranks['user2'],
                        'User3': individual_ranks['user3'],
                        'User4': individual_ranks['user4'],
                        'Status': "❌ DRAFTED" if player_id in st.session_state.drafted_players else "✅ Available",
                        'player_id': player_id
                    })
            
            # Sort by consensus ranking
            consensus_data.sort(key=lambda x: x['Consensus'] if x['Consensus'] != '-' else float('inf'))
            
            # Display as dataframe
            df = pd.DataFrame(consensus_data)
            st.dataframe(df.drop('player_id', axis=1), use_container_width=True)
        else:
            st.info("No player rankings yet. Add some rankings in the 'My Rankings' tab!")
    
    with tab3:
        st.header("Draft Board")
        
        if 'draft_info' in st.session_state:
            draft_info = st.session_state.draft_info
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Draft Type", draft_info.get('type', 'N/A'))
            with col2:
                st.metric("Total Picks", len(st.session_state.drafted_players))
            with col3:
                st.metric("Status", draft_info.get('status', 'N/A'))
            
            # Show recent picks
            st.subheader("Recent Draft Picks")
            if st.session_state.drafted_players:
                st.write(f"Players drafted: {len(st.session_state.drafted_players)}")
                # You could expand this to show actual pick details
            else:
                st.info("No picks made yet")
                
            # Refresh button
            if st.button("🔄 Refresh Draft"):
                if draft_id:
                    picks = get_draft_picks(draft_id)
                    st.session_state.drafted_players = {pick['player_id'] for pick in picks if pick['player_id']}
                    st.success("Draft refreshed!")
                    st.rerun()
        else:
            st.info("Enter a Draft ID in the sidebar to view draft information")
    
    with tab4:
        st.header("Player Database")
        st.info(f"Total players loaded: {len(st.session_state.all_players)}")
        
        # Simple player browser
        if st.session_state.all_players:
            # Position filter
            positions = set()
            for player_data in st.session_state.all_players.values():
                if player_data and player_data.get('position'):
                    positions.add(player_data.get('position'))
            
            selected_position = st.selectbox("Filter by Position", ['All'] + sorted(positions))
            
            # Team filter
            teams = set()
            for player_data in st.session_state.all_players.values():
                if player_data and player_data.get('team'):
                    teams.add(player_data.get('team'))
            
            selected_team = st.selectbox("Filter by Team", ['All'] + sorted(teams))
            
            # Display filtered players
            filtered_players = []
            for player_id, player_data in st.session_state.all_players.items():
                if player_data:
                    if selected_position != 'All' and player_data.get('position') != selected_position:
                        continue
                    if selected_team != 'All' and player_data.get('team') != selected_team:
                        continue
                    
                    filtered_players.append({
                        'Name': f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}",
                        'Position': player_data.get('position', 'N/A'),
                        'Team': player_data.get('team', 'N/A'),
                        'Status': "❌ DRAFTED" if player_id in st.session_state.drafted_players else "✅ Available"
                    })
            
            # Show results
            st.write(f"Showing {len(filtered_players)} players")
            if filtered_players:
                df = pd.DataFrame(filtered_players)
                st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()