import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initAuth } from './api/auth'

// Login must resolve before anything renders — every screen needs the
// token this sets up, and there is no useful "logged out" view to show.
initAuth().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
