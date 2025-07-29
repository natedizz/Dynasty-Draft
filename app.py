import streamlit as st
import pandas as pd
import requests

# Configuration
SLEEPER_BASE_URL = "https://api.sleeper.app/v1"
DRAFT_ID = "1255223076447072256"

# User configuration with cool emojis
USER_OPTIONS = {
    'nathan': '🔥 Nathan',
    'nathaniel': '⚡ Nathaniel', 
    'jack': '🚀 Jack',
    'kyle': '💎 Kyle'
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
    
    for idx, row in df.iterrows():
        player_name = row['PLAYER NAME'].strip()
        
        # Try to find matching Sleeper player
        for sleeper_id, sleeper_player in sleeper_players.items():
            if sleeper_player:
                sleeper_full_name = f"{sleeper_player.get('first_name', '')} {sleeper_player.get('last_name', '')}".strip()
                
                # Check if names match (case insensitive)
                if player_name.lower() == sleeper_full_name.lower():
                    df.at[idx, 'sleeper_id'] = sleeper_id
                    if sleeper_id in drafted_player_ids:
                        df.at[idx, 'drafted'] = True
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
    tab1 = st.tabs(["📊 All Players"])[0]
    
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

if __name__ == "__main__":
    main() 