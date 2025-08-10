# Composio Integration Documentation

## Overview
This document describes the integration of Composio for OAuth authentication and tool execution in the backend, specifically for Google Docs, Gmail, and Linear.

## Architecture

### Backend Components

1. **Composio Service** (`gateway/service/composio_service.py`)
   - Handles all Composio SDK interactions
   - Manages entities, connections, and tool execution
   - Formats responses for frontend compatibility

2. **Authentication Controller** (`gateway/controller/composio_auth_controller.py`)
   - **POST /api/composio/auth/initiate** - Start OAuth flow
   - **GET /api/composio/auth/status/{entity_id}/{app}** - Check connection status
   - **GET /api/composio/auth/connections/{entity_id}** - List all connections
   - **POST /api/composio/auth/disconnect/{entity_id}/{app}** - Disconnect app

3. **Documents Controller** (`gateway/controller/composio_docs_controller.py`)
   - **GET /api/documents** - Fetch Google Docs (uses GOOGLEDOCS_SEARCH_DOCUMENTS)
   - **GET /api/documents/{document_id}** - Get specific document
   - **POST /api/documents/{document_id}/generate** - Generate content
   - **GET /api/documents/mock/test-data** - Mock data for testing

### Frontend Components

1. **API Client** (`client/src/lib/composio.ts`)
   - Functions for auth, document fetching, and app management

2. **Auth Button Component** (`client/src/components/AuthButton.svelte`)
   - Reusable component for OAuth authentication
   - Handles redirect flow and status polling
   - Visual feedback for connection status

3. **Updated App Component** (`client/src/App.svelte`)
   - Integrates auth buttons for Google Docs, Gmail, Linear
   - Fetches real documents when connected
   - Falls back to sample data when not connected

## Authentication Flow

1. **Initiate Connection**
   ```javascript
   // Frontend
   const result = await initiateAuth('googledocs', 'user-123');
   window.open(result.redirect_url);
   ```

2. **User Completes OAuth**
   - User authenticates on Google/Gmail/Linear
   - Provider redirects back to callback URL

3. **Poll for Status**
   ```javascript
   // Frontend polls until connected
   const status = await checkConnectionStatus('user-123', 'googledocs');
   if (status.connected) {
     // Connection successful
   }
   ```

4. **Use Connected Services**
   ```javascript
   // Fetch documents
   const docs = await fetchDocuments('user-123');
   ```

## Configuration

### Environment Variables
Add to `.env`:
```bash
COMPOSIO_API_KEY=your_composio_api_key_here
```

### Entity Management
Each user should have a unique entity_id:
- Use user's database ID or UUID
- Same entity can have multiple app connections
- Entity persists across sessions

## Testing

### 1. Test Backend Endpoints
```bash
# Start the backend
./start_services.sh

# Test mock documents
curl http://localhost:8000/api/documents/mock/test-data

# Test auth initiation (will fail without valid Composio API key)
curl -X POST http://localhost:8000/api/composio/auth/initiate \
  -H "Content-Type: application/json" \
  -d '{"app": "googledocs", "entity_id": "test-user"}'
```

### 2. Test Frontend
```bash
# In client directory
cd client
npm install
npm run dev

# Open http://localhost:5173
# Use "Use mock data" checkbox for testing without auth
```

### 3. Test Full OAuth Flow
1. Ensure valid COMPOSIO_API_KEY in `.env`
2. Click "Connect Google Docs" button
3. Complete OAuth in popup window
4. Documents should load automatically

## Troubleshooting

### Common Issues

1. **"COMPOSIO_API_KEY not found"**
   - Add COMPOSIO_API_KEY to `.env` file
   - Restart backend services

2. **OAuth popup blocked**
   - Check browser popup settings
   - Allow popups from localhost

3. **Connection timeout**
   - Check Composio dashboard for connection status
   - Verify OAuth credentials in Composio settings

4. **No documents showing**
   - Verify Google Docs connection is active
   - Check browser console for errors
   - Try "Use mock data" to verify UI works

### Debug Mode
The frontend includes debug controls:
- **"Use mock data"** - Test without authentication
- **"Refresh"** - Reload documents
- Check browser console for detailed errors

## Next Steps

1. **Production Considerations**
   - Remove debug controls from frontend
   - Implement proper user session management
   - Add error tracking and monitoring
   - Set up OAuth callback URLs for production

2. **Additional Features**
   - Implement document search
   - Add document creation/editing
   - Integrate Gmail for sending documents
   - Add Linear issue creation from documents

3. **Security**
   - Implement rate limiting
   - Add request validation
   - Secure entity_id management
   - Add CSRF protection

## API Reference

### Composio Tools Used
- **GOOGLEDOCS_SEARCH_DOCUMENTS** - List all Google Docs
- **GOOGLEDOCS_GET_DOCUMENT** - Get specific document (planned)
- **GMAIL_SEND_EMAIL** - Send emails (planned)
- **LINEAR_CREATE_ISSUE** - Create Linear issues (planned)

### Response Formats
Documents are formatted to match frontend expectations:
```typescript
interface GoogleDoc {
  id: string;
  name: string;
  mimeType: string;
  createdTime: string;
  modifiedTime?: string;
  webViewLink?: string;
  size: string;
  starred: boolean;
  trashed: boolean;
  shared: boolean;
  owners?: Array<{
    displayName: string;
    emailAddress: string;
    photoLink?: string;
  }>;
  lastModifyingUser?: {
    displayName: string;
    emailAddress: string;
    photoLink?: string;
  };
}
```