## Template Overview

This is a modern React + TypeScript + Vite template optimized for fast development with shadcn/ui components. It serves as a comprehensive starting point for web applications with a complete design system and development toolchain.

## Development Commands

- `bun run dev` - Start development server with hot module replacement
- `bun run build` - Build for production (runs TypeScript compiler then Vite build)
- `bun run lint` - Run ESLint on all TypeScript/TSX files
- `bun run preview` - Preview production build locally

## Development Rules

### Core Development Principles
1. **Package Management**: Always use `bun`/`bunx` instead of `npm`/`npx` for all package management and script execution
2. **Component Reuse**: Always reuse shadcn/ui components instead of building UI components from scratch
3. **Design Consistency**: Use default font and design system unless explicitly instructed otherwise
4. **Code Quality**: Always run `bun run lint` after making changes to ensure code quality
5. **Component Architecture**: Separate complex component variants into dedicated files to avoid ESLint fast-refresh issues

### Planning and Thinking Workflow
6. **Use TodoWrite Proactively**: Create todo lists for multi-step tasks to track progress and ensure completeness
7. **Plan Before Coding**: For complex features, analyze existing patterns first, then plan the implementation approach
8. **Break Down Features**: Split large features into smaller, testable components that can be developed incrementally
9. **Context Analysis**: Before making changes, understand the existing codebase patterns, imports, and conventions

### Efficient Development Process
10. **Batch Tool Calls**: Use multiple tool calls in single messages to reduce round trips (e.g., parallel file reads, searches)
11. **Search Strategy**: Use Task tool for open-ended searches, Glob/Grep for specific patterns, Read for known files
12. **Component Discovery**: Always check `src/components/ui/` and `src/lib/` for existing utilities before creating new ones
13. **Import Path Consistency**: Use `@/` aliases for all internal imports to maintain clean, absolute paths

### Testing and Quality Assurance
14. **Development Testing**: Run `bun run dev` to test changes in browser during development
15. **Build Verification**: Run `bun run build` to catch TypeScript errors and build issues early
16. **Lint Integration**: Integrate linting into development workflow, not just as final step
17. **Component Testing**: Test component variants and edge cases manually in development server

### Error Prevention Strategies
18. **TypeScript First**: Leverage TypeScript's type checking to catch errors before runtime
19. **Dependency Verification**: Check `package.json` and existing imports before assuming library availability
20. **Pattern Matching**: Follow existing code conventions, especially for styling and component structure
21. **Progressive Enhancement**: Build features incrementally, testing each step before proceeding

### Feature Addition Best Practices
22. **Existing Pattern Analysis**: Study similar components/features in codebase before implementing new ones
23. **Minimal Viable Implementation**: Start with simplest working version, then enhance iteratively
24. **Component Composition**: Build complex UI by composing simpler, reusable components
25. **State Management**: Keep component state minimal and lift state up when needed for sharing

### Time-Saving Optimization
26. **File Organization**: Keep related files close (components, variants, utilities) for easier maintenance
27. **Utility Reuse**: Leverage existing utilities like `cn()`, component variants, and CSS custom properties
28. **Template Patterns**: Use established shadcn/ui patterns for consistent, accessible components
29. **Development Shortcuts**: Use Vite's fast refresh and hot module replacement for rapid iteration
30. **Documentation Updates**: Update component documentation and examples as you build for future reference

## Project Architecture

### Tech Stack
- **Frontend Framework**: React 19.1.0 with TypeScript 5.8.3
- **Build Tool**: Vite 7.0.0 with @vitejs/plugin-react for fast refresh
- **Styling**: Tailwind CSS 4.1.11 with @tailwindcss/vite plugin
- **UI Components**: shadcn/ui compatible setup with class-variance-authority 0.7.1
- **Icon Library**: Lucide React 0.525.0 for consistent iconography
- **Development**: ESLint 9.29.0 with TypeScript and React-specific rules

### Key Dependencies
**Production Dependencies:**
- `@radix-ui/react-slot` (1.2.3) - Primitive for component composition
- `class-variance-authority` (0.7.1) - Component variant management
- `clsx` (2.1.1) + `tailwind-merge` (3.3.1) - Conditional class handling
- `lucide-react` (0.525.0) - Comprehensive icon library

**Development Dependencies:**
- `@vitejs/plugin-react-swc` (3.10.2) - Fast refresh with SWC
- `typescript-eslint` (8.34.1) - Modern TypeScript linting
- `tw-animate-css` (1.3.4) - Additional Tailwind animations

### Configuration Architecture
- **Path Aliases**: `@/*` maps to `./src/*` for clean imports
- **TypeScript**: Project references with separate app and node configs
- **ESLint**: Flat config with TypeScript, React Hooks, and React Refresh rules
- **Vite**: Optimized for React with Tailwind CSS integration

### Project Structure
```
src/
  ├── components/        # UI components (shadcn/ui compatible)
  │   └── ui/           # Base UI primitives (Button, Card, etc.)
  ├── lib/              # Utility functions and component variants
  │   ├── utils.ts      # cn() utility and helpers
  │   └── button-variants.ts  # Component variant definitions
  ├── assets/           # Static assets (images, icons)
  ├── App.tsx           # Main application component
  ├── main.tsx          # Application entry point
  ├── index.css         # Global styles and CSS variables
  └── vite-env.d.ts     # Vite environment types
```

### Component Development
- Use the `cn()` utility from `@/lib/utils` for conditional className handling
- Follow shadcn/ui patterns for component structure and styling
- Components are expected in `@/components` with UI primitives in `@/components/ui`
- Import paths use `@/` alias for clean, absolute imports
- Complex variants should be extracted to `/src/lib/` files (e.g., `button-variants.ts`)

### Styling System
**Tailwind CSS 4 Configuration:**
- **CSS Variables**: Comprehensive theming system with semantic color tokens
- **Dark Mode**: Automatic support via CSS custom properties and `.dark` class
- **Border Radius**: Configurable via `--radius` CSS variable (default: 0.625rem)
- **Color Palette**: Full spectrum with oklch() color space for better perceptual uniformity
- **Animations**: Extended with `tw-animate-css` for additional effects

**Color Token System:**
- Background/Foreground pairs for consistent contrast
- Primary/Secondary/Accent semantic colors
- Chart colors (chart-1 through chart-5) for data visualization
- Sidebar-specific tokens for complex layouts
- Muted and destructive variants for different UI states

**Custom CSS Features:**
- `@custom-variant dark` for better dark mode handling
- Comprehensive CSS variable mapping in `@theme inline`
- Base layer styles for consistent border and outline behavior

### TypeScript Configuration
**Strict Mode Features:**
- `noUnusedLocals` and `noUnusedParameters` for clean code
- `noFallthroughCasesInSwitch` for safer switch statements
- `noUncheckedSideEffectImports` for better tree shaking
- `erasableSyntaxOnly` for type-only import optimization
- `verbatimModuleSyntax` for explicit import/export intent

**Build Optimization:**
- Separate build info files for faster incremental builds
- Module detection set to "force" for ESM compatibility
- Bundle-first module resolution for Vite compatibility

### Lint Rules & Code Quality
- **ESLint Configuration**: Flat config format with global ignores
- **TypeScript Rules**: Full recommended ruleset with strict checking
- **React Rules**: React Hooks and React Refresh compatibility
- **Performance**: `react-refresh/only-export-components` for fast refresh
- **File Targeting**: TypeScript/TSX files only with browser globals

### Development Workflow
1. **Component Creation**: Start with existing shadcn/ui patterns
2. **Variant Management**: Use class-variance-authority for complex components
3. **Styling**: Leverage CSS variables and semantic tokens
4. **Testing**: Run `bun run lint` for code quality checks
5. **Building**: Use `bun run build` for production optimization

### Template Benefits
- **Zero Configuration**: Ready-to-use development environment
- **Modern Stack**: Latest stable versions of all dependencies
- **Performance Optimized**: SWC for fast refresh, optimal Vite configuration
- **Design System Ready**: Complete theming and component architecture
- **Type Safe**: Comprehensive TypeScript configuration
- **Accessible**: Radix UI primitives for keyboard and screen reader support


### Quick Setup Instructions

1. **Initialize Project**:
   ```bash
   mkdir my-vite-project && cd my-vite-project
   bun init -y
   ```

2. **Install Dependencies**: Copy the `package.json` above and run:
   ```bash
   bun install
   ```

3. **Create Configuration Files**: Copy all config files (vite.config.ts, tsconfig.json, etc.)

4. **Setup Source Structure**:
   ```bash
   mkdir -p src/{components/ui,lib,assets}
   ```

5. **Copy Essential Files**: Create all files listed above in their respective locations

6. **Start Development**:
   ```bash
   bun run dev
   ```

This template provides a complete, production-ready React application with modern tooling, comprehensive TypeScript configuration, and a full design system ready for immediate development.