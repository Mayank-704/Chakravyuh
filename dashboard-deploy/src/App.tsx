import React, { ErrorInfo, ReactNode, useEffect, useRef, useState } from 'react';
import { Menu } from 'lucide-react';
import Dashboard from './components/Dashboard';

type ThemeName = 'current' | 'light' | 'clean';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error: error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // You can also log the error to an error reporting service
    console.error("Uncaught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return (
        <div className="p-10 text-red-500">
          <h1 className="text-2xl font-bold">Something went wrong.</h1>
          <pre>{this.state.error?.message}</pre>
        </div>
      );
    }

    return this.props.children;
  }
}


function App() {
  const [theme, setTheme] = useState<ThemeName>('current');
  const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false);
  const themeMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const savedThemeRaw = localStorage.getItem('chakravyuh-theme');
    const savedTheme = savedThemeRaw === 'neo' ? 'clean' : (savedThemeRaw as ThemeName | null);
    const activeTheme = savedTheme ?? 'current';
    setTheme(activeTheme);
    document.documentElement.setAttribute('data-theme', activeTheme);
  }, []);

  const handleThemeChange = (nextTheme: ThemeName) => {
    setTheme(nextTheme);
    localStorage.setItem('chakravyuh-theme', nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
    setIsThemeMenuOpen(false);
  };

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (!themeMenuRef.current) return;
      if (!themeMenuRef.current.contains(event.target as Node)) {
        setIsThemeMenuOpen(false);
      }
    };

    if (isThemeMenuOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isThemeMenuOpen]);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-black font-sans text-slate-300 theme-shell">
        <div ref={themeMenuRef} className="fixed top-2 right-2 z-[3000]">
          <button
            type="button"
            aria-label="Open theme settings"
            className="theme-fab"
            onClick={() => setIsThemeMenuOpen((prev) => !prev)}
          >
            <Menu size={16} />
          </button>

          {isThemeMenuOpen && (
            <div className="theme-panel theme-panel-compact rounded-lg px-2 py-1 shadow-xl border theme-popover">
              <label htmlFor="theme-switcher" className="text-[9px] font-bold tracking-wider uppercase block mb-0.5 theme-muted-text">
                Theme
              </label>
              <select
                id="theme-switcher"
                value={theme}
                onChange={(e) => handleThemeChange(e.target.value as ThemeName)}
                className="text-xs px-2 py-1 rounded-md theme-select"
              >
                <option value="current">Current</option>
                <option value="light">Light</option>
                <option value="clean">Clean Theme</option>
              </select>
            </div>
          )}
        </div>
        <Dashboard />
      </div>
    </ErrorBoundary>
  );
}

export default App;