import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import Incidents from './pages/Incidents'
import Workflow from './pages/Workflow'
import Monitoring from './pages/Monitoring'
import Costs from './pages/Costs'
import Kubernetes from './pages/Kubernetes'
import Logs from './pages/Logs'
import Settings from './pages/Settings'

export default function App() {
  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 min-w-0">
        <Routes>
          <Route
            path="/"
            element={<>
              <Navbar title="Dashboard" subtitle="Live agent pipeline & fleet health" />
              <Dashboard />
            </>}
          />
          <Route
            path="/incidents"
            element={<>
              <Navbar title="Incidents" subtitle="All agent runs, filterable by severity & status" />
              <Incidents />
            </>}
          />
          <Route
            path="/workflow"
            element={<>
              <Navbar title="Workflow" subtitle="Run detail & pipeline timeline" />
              <Workflow />
            </>}
          />
          <Route
            path="/monitoring"
            element={<>
              <Navbar title="Monitoring" subtitle="Agent performance & alarm telemetry" />
              <Monitoring />
            </>}
          />
          <Route
            path="/costs"
            element={<>
              <Navbar title="Costs" subtitle="AWS spend and FinOps savings opportunities" />
              <Costs />
            </>}
          />
          <Route
            path="/kubernetes"
            element={<>
              <Navbar title="Kubernetes" subtitle="Cluster nodes & pod health" />
              <Kubernetes />
            </>}
          />
          <Route
            path="/logs"
            element={<>
              <Navbar title="Logs" subtitle="Live agent output" />
              <Logs />
            </>}
          />
          <Route
            path="/settings"
            element={<>
              <Navbar title="Settings" subtitle="Environment & connection status" />
              <Settings />
            </>}
          />
        </Routes>
      </div>
    </div>
  )
}
