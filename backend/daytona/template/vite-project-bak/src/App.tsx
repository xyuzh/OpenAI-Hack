import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-2xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight mb-2">Vite + React</h1>
          <p className="text-muted-foreground">
            A modern React application with shadcn/ui components
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Counter Example</CardTitle>
            <CardDescription>
              Click the button below to increment the counter
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center space-y-4">
              <div className="text-2xl font-mono">
                Count: {count}
              </div>
              <Button onClick={() => setCount((count) => count + 1)}>
                Increment Counter
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Getting Started</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Edit <code className="bg-muted px-1 py-0.5 rounded text-xs">src/App.tsx</code> and save to test hot module replacement.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default App
