import { createSlice } from "@reduxjs/toolkit";

/**
 * Placeholder slice for the Redux store scaffold (Schritt 0).
 * Real feature slices (auth, runs, wizard, ...) land in `src/features/`
 * as the roadmap steps are implemented.
 */
interface AppState {
  status: "idle";
}

const initialState: AppState = { status: "idle" };

const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {},
});

export default appSlice.reducer;
