import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { SidebarProvider } from './context/SidebarProvider';
import { AppRoutes } from './routes/AppRoutes';
import { queryClient } from './lib/queryClient';
import './App.css';
import { ToastProvider } from './lib/ToastProvider';


function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <SidebarProvider>
            <div>
              <AppRoutes />
            </div>
          </SidebarProvider>
        </AuthProvider>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
      <ToastProvider />
    </QueryClientProvider>
  );
}

export default App;
