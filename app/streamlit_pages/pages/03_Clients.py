import streamlit as st
import requests
import pandas as pd
from app.streamlit_pages.components.auth import auth

st.set_page_config(
    page_title="Clients Management",
    page_icon="👥",
    layout="wide"
)

API_BASE_URL = "http://localhost:8000/api/v1"

def get_clients(search_query=None):
    """Fetch clients from API"""
    try:
        headers = auth.get_headers()
        params = {}
        if search_query:
            params["search"] = search_query
        
        response = requests.get(f"{API_BASE_URL}/clients/", 
                              headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_client_groups():
    """Fetch client groups from API"""
    try:
        headers = auth.get_headers()
        response = requests.get(f"{API_BASE_URL}/clients/groups/", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def create_client(data):
    """Create new client"""
    try:
        headers = auth.get_headers()
        response = requests.post(f"{API_BASE_URL}/clients/", 
                                json=data, headers=headers)
        return response.status_code == 200, response.json() if response.status_code != 200 else None
    except Exception as e:
        return False, str(e)

def update_client(client_id, data):
    """Update client"""
    try:
        headers = auth.get_headers()
        response = requests.put(f"{API_BASE_URL}/clients/{client_id}", 
                               json=data, headers=headers)
        return response.status_code == 200, response.json() if response.status_code != 200 else None
    except Exception as e:
        return False, str(e)

def delete_client(client_id):
    """Delete client"""
    try:
        headers = auth.get_headers()
        response = requests.delete(f"{API_BASE_URL}/clients/{client_id}", 
                                  headers=headers)
        return response.status_code == 200
    except:
        return False

def get_client_stats(client_id):
    """Get client statistics"""
    try:
        headers = auth.get_headers()
        response = requests.get(f"{API_BASE_URL}/clients/{client_id}/stats", 
                               headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def create_client_group(data):
    """Create new client group"""
    try:
        headers = auth.get_headers()
        response = requests.post(f"{API_BASE_URL}/clients/groups/", 
                                json=data, headers=headers)
        return response.status_code == 200
    except:
        return False

def main():
    st.title("👥 Clients Management")
    
    # Check authentication
    if not auth.is_authenticated():
        st.error("Please login first")
        if st.button("Go to Login"):
            st.switch_page("01_Dashboard.py")
        return
    
    # Show user info in sidebar
    auth.render_user_info()
    
    # Navigation in sidebar
    st.sidebar.title("Navigation")
    
    if st.sidebar.button("🏠 Dashboard"):
        st.switch_page("01_Dashboard.py")
    
    if st.sidebar.button("🏨 Accommodations"):
        st.switch_page("pages/02_Accommodations.py")
    
    if st.sidebar.button("👥 Clients", type="primary"):
        st.switch_page("pages/03_Clients.py")
    
    # Check user role for write operations
    user_info = auth.get_user_info()
    is_staff = user_info and user_info.get('role') == 'staff'
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📋 View Clients", "👥 Client Groups", "➕ Add New"])
    
    with tab1:
        st.header("Client Database")
        
        # Search functionality
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_query = st.text_input("🔍 Search clients by name, phone, or email", 
                                       placeholder="Enter search term...")
        with search_col2:
            search_button = st.button("Search", type="primary")
        
        # Fetch and display clients
        clients = get_clients(search_query if search_query else None)
        
        if clients:
            # Convert to DataFrame for better display
            df_data = []
            for client in clients:
                group_name = client.get("group", {}).get("name", "") if client.get("group") else ""
                social_links_str = ", ".join(client.get("social_links", {}).keys()) if client.get("social_links") else ""
                car_numbers_str = ", ".join(client.get("car_numbers", [])) if client.get("car_numbers") else ""
                
                df_data.append({
                    "ID": client["id"],
                    "Name": f"{client['first_name']} {client['last_name']}",
                    "Phone": client.get("phone", ""),
                    "Email": client.get("email", ""),
                    "Group": group_name,
                    "Rating": client.get("rating", 0.0) or 0.0,
                    "Social": social_links_str,
                    "Cars": car_numbers_str,
                    "Comments": (client.get("comments", "") or "")[:30] + "..." if (client.get("comments", "") or "") and len(client.get("comments", "") or "") > 30 else (client.get("comments", "") or "")
                })
            
            df = pd.DataFrame(df_data)
            
            # Display dataframe
            st.dataframe(df, use_container_width=True)
            
            # Display editing capabilities for staff
            if is_staff:
                st.markdown("---")
                st.write("**Edit Clients:**")
                
                # Use selectbox for editing
                client_options = {f"{client['first_name']} {client['last_name']} - {client.get('phone', 'No phone')}": i for i, client in enumerate(clients)}
                
                if client_options:
                    selected_display = st.selectbox("Choose client to edit:", [""] + list(client_options.keys()))
                    
                    if selected_display:
                        selected_idx = client_options[selected_display]
                        selected_client = clients[selected_idx]
                        
                        st.subheader(f"Edit Client: {selected_client['first_name']} {selected_client['last_name']}")
                        
                        # Get client groups for dropdown
                        client_groups = get_client_groups()
                        group_options = {"No Group": None}
                        group_options.update({group["name"]: group["id"] for group in client_groups})
                        
                        with st.form(f"edit_client_{selected_client['id']}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                new_first_name = st.text_input("First Name", value=selected_client["first_name"])
                                new_last_name = st.text_input("Last Name", value=selected_client["last_name"])
                                new_phone = st.text_input("Phone", value=selected_client.get("phone", ""))
                                new_email = st.text_input("Email", value=selected_client.get("email", ""))
                                
                                # Group selection
                                current_group_name = selected_client.get("group", {}).get("name", "") if selected_client.get("group") else "No Group"
                                if current_group_name not in group_options:
                                    current_group_name = "No Group"
                                selected_group_name = st.selectbox("Group", 
                                                                 list(group_options.keys()),
                                                                 index=list(group_options.keys()).index(current_group_name))
                                selected_group_id = group_options[selected_group_name]
                            
                            with col2:
                                new_rating = st.number_input("Rating", value=selected_client.get("rating", 0.0) or 0.0, 
                                                           min_value=0.0, max_value=5.0, step=0.1)
                                
                                # Social links (simplified - just text input for now)
                                current_social = selected_client.get("social_links", {}) or {}
                                social_links_text = ", ".join([f"{k}:{v}" for k, v in current_social.items()])
                                new_social_links_text = st.text_input("Social Links", 
                                                                     value=social_links_text,
                                                                     help="Format: vk:link, instagram:link")
                                
                                # Car numbers
                                current_cars = selected_client.get("car_numbers", []) or []
                                cars_text = ", ".join(current_cars)
                                new_cars_text = st.text_input("Car Numbers", 
                                                             value=cars_text,
                                                             help="Comma separated: A123BC78, B456DE99")
                                
                                new_photo_url = st.text_input("Photo URL", value=selected_client.get("photo_url", ""))
                                new_comments = st.text_area("Comments", value=selected_client.get("comments", ""))
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.form_submit_button("Update", type="primary"):
                                    # Parse social links
                                    social_links = {}
                                    if new_social_links_text:
                                        for item in new_social_links_text.split(","):
                                            if ":" in item:
                                                key, value = item.strip().split(":", 1)
                                                social_links[key] = value
                                    
                                    # Parse car numbers
                                    car_numbers = []
                                    if new_cars_text:
                                        car_numbers = [car.strip() for car in new_cars_text.split(",") if car.strip()]
                                    
                                    update_data = {
                                        "first_name": new_first_name,
                                        "last_name": new_last_name,
                                        "phone": new_phone or None,
                                        "email": new_email or None,
                                        "social_links": social_links if social_links else None,
                                        "car_numbers": car_numbers if car_numbers else None,
                                        "photo_url": new_photo_url or None,
                                        "rating": new_rating,
                                        "comments": new_comments or None,
                                        "group_id": selected_group_id
                                    }
                                    
                                    success, error = update_client(selected_client["id"], update_data)
                                    if success:
                                        st.success("Client updated successfully!")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to update client: {error}")
                            
                            with col2:
                                if st.form_submit_button("View Stats", type="secondary"):
                                    stats = get_client_stats(selected_client["id"])
                                    if stats:
                                        st.info(f"Visits: {stats.get('visits_count', 0)}, Total Spent: ${stats.get('total_spent', 0.0)}")
                                    else:
                                        st.error("Failed to load statistics")
                            
                            with col3:
                                if st.form_submit_button("Delete", type="secondary"):
                                    if st.session_state.get("confirm_delete"):
                                        if delete_client(selected_client["id"]):
                                            st.success("Client deleted successfully!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to delete client")
                                    else:
                                        st.session_state["confirm_delete"] = True
                                        st.warning("Click Delete again to confirm")
            else:
                st.info("Staff role required for editing clients")
        else:
            st.info("No clients found" + (f" for search '{search_query}'" if search_query else ""))
    
    with tab2:
        st.header("Client Groups")
        
        # Fetch and display client groups
        client_groups = get_client_groups()
        
        if client_groups:
            for group in client_groups:
                with st.expander(f"👥 {group['name']}"):
                    st.write(f"**Created:** {group['created_at']}")
                    # Could add group statistics here in future
        else:
            st.info("No client groups found")
        
        # Add new client group (staff only)
        if is_staff:
            st.subheader("Add New Client Group")
            
            with st.form("add_client_group"):
                group_name = st.text_input("Group Name", placeholder="e.g., Семья Ивановых, Компания друзей")
                
                if st.form_submit_button("Create Group", type="primary"):
                    if group_name:
                        group_data = {"name": group_name}
                        
                        if create_client_group(group_data):
                            st.success("Client group created successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to create client group")
                    else:
                        st.error("Group name is required")
        else:
            st.info("Staff role required for creating client groups")
    
    with tab3:
        st.header("Add New Client")
        
        if not is_staff:
            st.info("Staff role required for adding clients")
            return
        
        # Get client groups for dropdown
        client_groups = get_client_groups()
        group_options = {"No Group": None}
        group_options.update({group["name"]: group["id"] for group in client_groups})
        
        with st.form("add_client"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("First Name*", placeholder="Иван")
                last_name = st.text_input("Last Name*", placeholder="Иванов")
                phone = st.text_input("Phone", placeholder="+7 999 123-45-67")
                email = st.text_input("Email", placeholder="ivan@example.com")
                
                # Group selection
                selected_group_name = st.selectbox("Group", list(group_options.keys()))
                selected_group_id = group_options[selected_group_name]
            
            with col2:
                rating = st.number_input("Rating", min_value=0.0, max_value=5.0, step=0.1, value=0.0)
                
                # Social links (simplified input)
                social_links_text = st.text_input("Social Links", 
                                                 placeholder="vk:https://vk.com/user, instagram:@username",
                                                 help="Format: platform:link, platform:link")
                
                # Car numbers
                cars_text = st.text_input("Car Numbers", 
                                         placeholder="A123BC78, B456DE99",
                                         help="Comma separated car numbers")
                
                photo_url = st.text_input("Photo URL", placeholder="https://example.com/photo.jpg")
                comments = st.text_area("Comments", placeholder="Additional notes about the client")
            
            if st.form_submit_button("Create Client", type="primary"):
                if first_name and last_name:
                    # Parse social links
                    social_links = {}
                    if social_links_text:
                        for item in social_links_text.split(","):
                            if ":" in item:
                                key, value = item.strip().split(":", 1)
                                social_links[key] = value
                    
                    # Parse car numbers
                    car_numbers = []
                    if cars_text:
                        car_numbers = [car.strip() for car in cars_text.split(",") if car.strip()]
                    
                    client_data = {
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone": phone or None,
                        "email": email or None,
                        "social_links": social_links if social_links else None,
                        "car_numbers": car_numbers if car_numbers else None,
                        "photo_url": photo_url or None,
                        "rating": rating,
                        "comments": comments or None,
                        "group_id": selected_group_id
                    }
                    
                    success, error = create_client(client_data)
                    if success:
                        st.success("Client created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to create client: {error}")
                else:
                    st.error("First name and last name are required")

if __name__ == "__main__":
    main()