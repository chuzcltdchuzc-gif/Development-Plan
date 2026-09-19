import { type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { AuthProvider } from '@/lib/auth-context';
import { RequireAuth } from '@/components/require-auth';
import NotFound from '@/pages/not-found';
import {
  Route,
  Switch,
  useLocation,
  Router as WouterRouter,
} from 'wouter';

import { Dashboard } from '@/pages/dashboard';
import { ParcelsRegistry } from '@/pages/parcels/index';
import { ParcelNew } from '@/pages/parcels/new';
import { ParcelDetail } from '@/pages/parcels/detail';
import { Verify } from '@/pages/verify';
import { SignIn } from '@/pages/sign-in';

const queryClient = new QueryClient();

function Router() {
  return (
    <RoutedErrorBoundary>
      <Switch>
        {/* Public: no session required. /verify is deliberately public — a
            registry-status check for anyone, not a governed screen. */}
        <Route path="/sign-in" component={SignIn} />
        <Route path="/verify" component={Verify} />

        {/* Governed screens: unauthenticated navigation redirects to sign-in
            rather than rendering anything. */}
        <Route path="/">
          <RequireAuth><Dashboard /></RequireAuth>
        </Route>
        <Route path="/parcels">
          <RequireAuth><ParcelsRegistry /></RequireAuth>
        </Route>
        <Route path="/parcels/new">
          <RequireAuth><ParcelNew /></RequireAuth>
        </Route>
        <Route path="/parcels/:id">
          <RequireAuth><ParcelDetail /></RequireAuth>
        </Route>

        <Route component={NotFound} />
      </Switch>
    </RoutedErrorBoundary>
  );
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          <AuthProvider>
            <Router />
          </AuthProvider>
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
