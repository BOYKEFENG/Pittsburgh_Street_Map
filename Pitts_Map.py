import streamlit as st
import time

# Initialize session state variables on first run.
if "startup_time" not in st.session_state:
    st.session_state.startup_time = time.time()  # When the app first loaded
if "run_count" not in st.session_state:
    st.session_state.run_count = 0

# Increment run count on every re-run.
st.session_state.run_count += 1

st.write("**App Startup Time:**", st.session_state.startup_time)
st.write("**Run Count:**", st.session_state.run_count)

# Simulate an expensive computation that should run only once.
if "expensive_result" not in st.session_state:
    st.write("Performing expensive computation...")
    time.sleep(2)  # Simulate a delay
    st.session_state.expensive_result = f"Result computed at {time.time()}"
else:
    st.write("Using cached expensive result.")

st.write("**Expensive Result:**", st.session_state.expensive_result)

# A button to simulate a user-triggered action.
if st.button("Click me"):
    st.write("Button clicked!")
    # Optionally update something in session state, but avoid forcing another computation.
    st.session_state.last_click = time.time()

if "last_click" in st.session_state:
    st.write("**Last Button Click Time:**", st.session_state.last_click)
