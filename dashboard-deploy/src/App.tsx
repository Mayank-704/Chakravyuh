import Dashboard from './components/Dashboard';
import React from 'react';

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return <div className="p-10 text-red-500"><h1 className="text-2xl font-bold">Something went wrong.</h1><pre>{this.state.error?.message}</pre></div>;
    }
    return this.props.children;
  }
}

function App() {
  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-black font-sans text-slate-300">
        <Dashboard />
      </div>
    </ErrorBoundary>
  );
}

export default App;