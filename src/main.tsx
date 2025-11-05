import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
// import UploadComponent from './uoload.tsx'
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
    {/* <UploadComponent /> */}
  </StrictMode>,
)
