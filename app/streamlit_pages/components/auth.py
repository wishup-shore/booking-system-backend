import streamlit as st
import requests
from typing import Optional


class AuthComponent:
    def __init__(self, api_base_url: str = "http://localhost:8000/api/v1"):
        self.api_base_url = api_base_url
    
    def login(self, username: str, password: str) -> bool:
        """Login user and store token in session state"""
        try:
            response = requests.post(
                f"{self.api_base_url}/auth/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                st.session_state["access_token"] = data["access_token"]
                st.session_state["user_authenticated"] = True
                return True
            else:
                return False
        except Exception as e:
            st.error(f"Login error: {str(e)}")
            return False
    
    def logout(self):
        """Logout user and clear session state"""
        if "access_token" in st.session_state:
            del st.session_state["access_token"]
        if "user_authenticated" in st.session_state:
            del st.session_state["user_authenticated"]
        if "user_info" in st.session_state:
            del st.session_state["user_info"]
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.get("user_authenticated", False)
    
    def get_token(self) -> Optional[str]:
        """Get current access token"""
        return st.session_state.get("access_token")
    
    def get_user_info(self) -> Optional[dict]:
        """Get current user info"""
        if not self.is_authenticated():
            return None
        
        if "user_info" in st.session_state:
            return st.session_state["user_info"]
        
        # Fetch user info from API
        try:
            headers = {"Authorization": f"Bearer {self.get_token()}"}
            response = requests.get(f"{self.api_base_url}/auth/me", headers=headers)
            
            if response.status_code == 200:
                user_info = response.json()
                st.session_state["user_info"] = user_info
                return user_info
            else:
                # Token might be invalid, logout
                self.logout()
                return None
        except Exception:
            self.logout()
            return None
    
    def require_auth(self):
        """Redirect to login if not authenticated"""
        if not self.is_authenticated():
            st.switch_page("01_Dashboard.py")
    
    def render_login_form(self):
        """Render login form"""
        st.header("🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if username and password:
                    if self.login(username, password):
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please enter both username and password")
    
    def render_user_info(self):
        """Render user info and logout button in sidebar"""
        user_info = self.get_user_info()
        if user_info:
            st.sidebar.write(f"👤 Logged in as: **{user_info['username']}**")
            st.sidebar.write(f"🏷️ Role: **{user_info['role']}**")
            
            if st.sidebar.button("Logout"):
                self.logout()
                st.rerun()
    
    def get_headers(self) -> dict:
        """Get authorization headers for API requests"""
        token = self.get_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}


# Global auth instance
auth = AuthComponent()