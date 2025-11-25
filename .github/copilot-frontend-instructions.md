---
description: Frontend-specific development guidelines for MagicToolbox
applyTo: 'frontend/**'
---

# Frontend Development Guidelines

## React + TypeScript Best Practices

### Component Structure
- Use functional components exclusively
- Keep components small and focused (single responsibility)
- Prefer composition over inheritance
- Co-locate related components, styles, and tests
- Use named exports for components

```typescript
// Good component structure
interface ToolCardProps {
  tool: Tool;
  onSelect: (toolId: string) => void;
}

export const ToolCard: React.FC<ToolCardProps> = ({ tool, onSelect }) => {
  const handleClick = () => onSelect(tool.id);
  
  return (
    <div className="tool-card" onClick={handleClick}>
      <h3>{tool.name}</h3>
      <p>{tool.description}</p>
    </div>
  );
};
```

### Code Style Guidelines
- **Naming Convention**: Use camelCase for variables, functions, and methods; PascalCase for components, types, interfaces, and enums
- **Indentation**: 2 spaces (no tabs) - strictly enforced
- Use ESLint with recommended TypeScript rules
- Use Prettier formatter (2 spaces, single quotes)
- File names: PascalCase for components (e.g., `ToolCard.tsx`), camelCase for utilities (e.g., `formatDate.ts`)
- Constants: UPPER_SNAKE_CASE for true constants (e.g., `MAX_FILE_SIZE`)
- Private methods/properties: prefix with underscore (e.g., `_handleInternalEvent`)
- Boolean variables: prefix with `is`, `has`, `should` (e.g., `isLoading`, `hasError`)

### TypeScript Usage
- Enable strict mode in `tsconfig.json`
- Define interfaces for all props and state
- Use type inference where possible
- Avoid `any` - use `unknown` for truly unknown types
- Create shared types in `src/types/`
- Use discriminated unions for state management

```typescript
// Define API response types
interface Tool {
  id: string;
  name: string;
  description: string;
  inputFormats: string[];
  outputFormats: string[];
}

// Use discriminated unions for loading states
type RequestState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string };
```

### State Management

#### React Query for Server State
- Use React Query for all API calls
- Implement proper cache invalidation
- Use query keys consistently
- Handle loading and error states
- Implement optimistic updates where appropriate

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Query keys in a separate file
export const toolKeys = {
  all: ['tools'] as const,
  lists: () => [...toolKeys.all, 'list'] as const,
  list: (filters: string) => [...toolKeys.lists(), { filters }] as const,
  details: () => [...toolKeys.all, 'detail'] as const,
  detail: (id: string) => [...toolKeys.details(), id] as const,
};

// Hook for fetching tools
export const useTools = () => {
  return useQuery({
    queryKey: toolKeys.lists(),
    queryFn: () => api.getTools(),
  });
};

// Hook for processing with a tool
export const useProcessTool = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: ProcessRequest) => api.processToolRequest(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: toolKeys.all });
    },
  });
};
```

#### Zustand for Client State
- Use Zustand for UI state (theme, sidebar, etc.)
- Keep stores small and focused
- Use slices for large stores
- Implement persist middleware for user preferences

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  toggleTheme: () => void;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: 'light',
      sidebarOpen: true,
      toggleTheme: () => set((state) => ({ 
        theme: state.theme === 'light' ? 'dark' : 'light' 
      })),
      toggleSidebar: () => set((state) => ({ 
        sidebarOpen: !state.sidebarOpen 
      })),
    }),
    { name: 'ui-storage' }
  )
);
```

### API Client Setup
- Use Axios with interceptors
- Centralize API configuration
- Handle authentication tokens automatically
- Implement retry logic for failed requests
- Type all API responses

```typescript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Handle token refresh or redirect to login
      localStorage.removeItem('accessToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### Form Handling
- Use React Hook Form for all forms
- Validate with Zod schemas
- Display validation errors inline
- Implement proper error recovery
- Disable submit during processing

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const toolOptionsSchema = z.object({
  quality: z.number().min(1).max(100),
  format: z.enum(['jpg', 'png', 'webp']),
  resize: z.boolean(),
});

type ToolOptionsForm = z.infer<typeof toolOptionsSchema>;

export const ToolOptionsForm: React.FC = () => {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<ToolOptionsForm>({
    resolver: zodResolver(toolOptionsSchema),
    defaultValues: { quality: 80, format: 'jpg', resize: false },
  });
  
  const onSubmit = async (data: ToolOptionsForm) => {
    // Process form data
  };
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input type="number" {...register('quality', { valueAsNumber: true })} />
      {errors.quality && <span>{errors.quality.message}</span>}
      <button type="submit" disabled={isSubmitting}>Submit</button>
    </form>
  );
};
```

### File Upload Handling
- Use drag-and-drop interface
- Show upload progress
- Validate file type and size on client
- Display preview when appropriate
- Handle upload errors gracefully

```typescript
import { useDropzone } from 'react-dropzone';

export const FileUpload: React.FC = () => {
  const [uploadProgress, setUploadProgress] = useState(0);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    onDrop: async (acceptedFiles) => {
      const file = acceptedFiles[0];
      if (!file) return;
      
      const formData = new FormData();
      formData.append('file', file);
      
      await uploadFile(formData, {
        onUploadProgress: (progressEvent) => {
          const progress = Math.round(
            (progressEvent.loaded * 100) / (progressEvent.total || 100)
          );
          setUploadProgress(progress);
        },
      });
    },
  });
  
  return (
    <div {...getRootProps()} className="dropzone">
      <input {...getInputProps()} />
      {isDragActive ? 'Drop files here' : 'Drag files or click to upload'}
      {uploadProgress > 0 && <progress value={uploadProgress} max={100} />}
    </div>
  );
};
```

### Routing
- Use React Router v6
- Implement lazy loading for routes
- Use nested routes for layouts
- Protect routes with auth guards
- Handle 404 pages

```typescript
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { lazy, Suspense } from 'react';

const HomePage = lazy(() => import('./pages/HomePage'));
const ToolPage = lazy(() => import('./pages/ToolPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));

const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      { index: true, element: <HomePage /> },
      {
        path: 'tools/:toolId',
        element: <ProtectedRoute><ToolPage /></ProtectedRoute>,
      },
      { path: 'login', element: <LoginPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export const App = () => (
  <Suspense fallback={<LoadingSpinner />}>
    <RouterProvider router={router} />
  </Suspense>
);
```

### Styling with Tailwind CSS
- Use Tailwind utility classes
- Create custom components for repeated patterns
- Use CSS modules for complex components
- Implement dark mode support
- Follow responsive design principles (mobile-first)

```typescript
// Use Tailwind classes directly
export const Button: React.FC<ButtonProps> = ({ children, variant = 'primary' }) => {
  const baseClasses = 'px-4 py-2 rounded-lg font-medium transition-colors';
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
  };
  
  return (
    <button className={`${baseClasses} ${variantClasses[variant]}`}>
      {children}
    </button>
  );
};
```

### Error Handling
- Use error boundaries for component errors
- Display user-friendly error messages
- Implement retry mechanisms
- Log errors to monitoring service
- Provide fallback UI

```typescript
import { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<
  { children: ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false, error: null };
  
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    // Send to error tracking service
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try again
          </button>
        </div>
      );
    }
    
    return this.props.children;
  }
}
```

### Performance Optimization
- Use React.memo for expensive components
- Implement virtualization for long lists
- Lazy load images and components
- Debounce search inputs
- Use code splitting
- Optimize bundle size

```typescript
import { memo } from 'react';
import { FixedSizeList } from 'react-window';

// Memoize component to prevent unnecessary re-renders
export const ToolListItem = memo<ToolListItemProps>(({ tool }) => (
  <div className="tool-item">{tool.name}</div>
));

// Virtualize long lists
export const ToolList: React.FC<{ tools: Tool[] }> = ({ tools }) => (
  <FixedSizeList
    height={600}
    itemCount={tools.length}
    itemSize={80}
    width="100%"
  >
    {({ index, style }) => (
      <div style={style}>
        <ToolListItem tool={tools[index]} />
      </div>
    )}
  </FixedSizeList>
);
```

### Accessibility
- Use semantic HTML elements
- Add ARIA labels where needed
- Ensure keyboard navigation works
- Maintain proper focus management
- Test with screen readers
- Ensure sufficient color contrast

```typescript
export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, children }) => {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);
  
  if (!isOpen) return null;
  
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="modal-overlay"
    >
      <div className="modal-content">
        {children}
        <button onClick={onClose} aria-label="Close modal">×</button>
      </div>
    </div>
  );
};
```

### Testing Guidelines
- Write tests for all components
- Use React Testing Library
- Test user interactions, not implementation
- Mock API calls
- Test error states
- Achieve >80% coverage

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { ToolCard } from './ToolCard';

describe('ToolCard', () => {
  const mockTool = {
    id: '1',
    name: 'Image Converter',
    description: 'Convert images',
    inputFormats: ['jpg', 'png'],
    outputFormats: ['webp'],
  };
  
  it('renders tool information', () => {
    render(<ToolCard tool={mockTool} onSelect={vi.fn()} />);
    expect(screen.getByText('Image Converter')).toBeInTheDocument();
  });
  
  it('calls onSelect when clicked', () => {
    const handleSelect = vi.fn();
    render(<ToolCard tool={mockTool} onSelect={handleSelect} />);
    fireEvent.click(screen.getByRole('button'));
    expect(handleSelect).toHaveBeenCalledWith('1');
  });
});
```

### Environment Variables
- Prefix all env vars with `VITE_`
- Never commit `.env` files
- Use `.env.example` as template
- Validate required env vars on startup
- Use different values per environment

```typescript
// src/config/env.ts
const requiredEnvVars = ['VITE_API_BASE_URL'] as const;

requiredEnvVars.forEach((envVar) => {
  if (!import.meta.env[envVar]) {
    throw new Error(`Missing required environment variable: ${envVar}`);
  }
});

export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
  environment: import.meta.env.MODE,
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
} as const;
```

### Build Optimization
- Configure Vite for optimal builds
- Use tree-shaking
- Enable gzip compression
- Optimize assets (images, fonts)
- Analyze bundle size regularly
- Implement cache-busting

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: ['@tanstack/react-query', 'zustand'],
        },
      },
    },
  },
});
```
