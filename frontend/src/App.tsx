import { Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from './auth/AuthContext'
import { AuditPage } from './pages/AuditPage'
import { DispatcherPage } from './pages/DispatcherPage'
import { ExportPage } from './pages/ExportPage'
import { LoginPage } from './pages/LoginPage'
import { SchedulePage } from './pages/SchedulePage'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<SchedulePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dispatcher" element={<DispatcherPage />} />
        <Route path="/export" element={<ExportPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
