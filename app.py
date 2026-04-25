import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Streamlit + Supabase Auth", layout="centered")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]


def sb_anon():
    """Client for auth calls (sign up / sign in / sign out)."""
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def sb_for_user(access_token: str):
    """Client configured with the user's JWT so RLS is enforced."""
    sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    sb.postgrest.auth(access_token)
    return sb


def set_session(auth_res):
    st.session_state["user"] = auth_res.user
    st.session_state["session"] = auth_res.session
    st.session_state["access_token"] = auth_res.session.access_token


def clear_session():
    for k in ["user", "session", "access_token"]:
        st.session_state.pop(k, None)


def signup_ui():
    st.subheader("Sign up")

    with st.form("signup_form"):
        email = st.text_input("Email", key="su_email")
        password = st.text_input("Password", type="password", key="su_password")
        submit = st.form_submit_button("Create account")

    if submit:
        if not email or not password:
            st.error("Please fill in email and password.")
            return

        try:
            res = sb_anon().auth.sign_up({"email": email, "password": password})

            # If email confirmations are enabled, session may be None
            if not res.session:
                st.success("Account created. Check your email to confirm, then come back and log in.")
                return

            set_session(res)
            st.success("Account created and logged in.")
            st.rerun()

        except Exception as e:
            st.error("Sign up failed.")
            st.exception(e)


def login_ui():
    st.subheader("Log in")

    with st.form("login_form"):
        email = st.text_input("Email", key="li_email")
        password = st.text_input("Password", type="password", key="li_password")
        submit = st.form_submit_button("Log in")

    if submit:
        if not email or not password:
            st.error("Please fill in email and password.")
            return

        try:
            res = sb_anon().auth.sign_in_with_password({"email": email, "password": password})
            set_session(res)
            st.success("Logged in.")
            st.rerun()

        except Exception as e:
            st.error("Login failed. Check credentials (and email confirmation settings).")
            # st.exception(e)  # uncomment if you want full error detail


def dashboard_ui():
    user = st.session_state["user"]
    token = st.session_state["access_token"]
    sb = sb_for_user(token)

    st.title("Dashboard")
    st.caption(f"Signed in as: {user.email}")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Refresh"):
            st.rerun()
    with col2:
        if st.button("Log out"):
            try:
                sb_anon().auth.sign_out()
            except Exception:
                pass
            clear_session()
            st.rerun()

    st.divider()

    st.subheader("Your notes (RLS protected)")

    # This SELECT is protected by RLS:
    # user only sees rows where owner_user_id == auth.uid()
    notes_res = (
        sb.table("notes")
        .select("id, title, created_at")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    notes = notes_res.data or []

    st.dataframe(notes, use_container_width=True)

    st.divider()
    st.subheader("Create a test note (also RLS protected)")

    with st.form("new_note"):
        title = st.text_input("Title", placeholder="e.g., First note")
        submit = st.form_submit_button("Create")

    if submit:
        if not title.strip():
            st.error("Please enter a title.")
            return

        # Insert row with owner_user_id set to the logged-in user
        sb.table("notes").insert(
            {"owner_user_id": user.id, "title": title.strip()}
        ).execute()

        st.success("Created.")
        st.rerun()


def main():
    # Simple routing
    if "access_token" not in st.session_state:
        st.title("Welcome")

        tab_login, tab_signup = st.tabs(["Log in", "Sign up"])
        with tab_login:
            login_ui()
        with tab_signup:
            signup_ui()
    else:
        dashboard_ui()


if __name__ == "__main__":
    main()