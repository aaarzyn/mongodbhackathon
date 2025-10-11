/**
 * API Test Page - Debug connection issues
 */

'use client';

import { useState } from 'react';

export default function TestPage() {
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  async function testAPI() {
    setLoading(true);
    setResult('Testing...\n');
    
    const apiUrl = 'http://localhost:8000';
    
    try {
      // Test 1: Health check
      setResult(prev => prev + '\n1. Testing health endpoint...');
      const healthResponse = await fetch(`${apiUrl}/health`);
      const healthData = await healthResponse.json();
      setResult(prev => prev + `\n✓ Health: ${JSON.stringify(healthData)}`);
      
      // Test 2: Top-rated movies
      setResult(prev => prev + '\n\n2. Testing top-rated movies...');
      const moviesResponse = await fetch(`${apiUrl}/api/movies/top-rated?limit=3`);
      const moviesData = await moviesResponse.json();
      setResult(prev => prev + `\n✓ Received ${moviesData.length} movies`);
      setResult(prev => prev + `\n  First movie: ${moviesData[0].title}`);
      
      // Test 3: Genre filter
      setResult(prev => prev + '\n\n3. Testing Action genre...');
      const actionResponse = await fetch(`${apiUrl}/api/movies/?genre=Action&limit=3`);
      const actionData = await actionResponse.json();
      setResult(prev => prev + `\n✓ Received ${actionData.length} Action movies`);
      
      setResult(prev => prev + '\n\n✅ ALL TESTS PASSED!');
    } catch (error: any) {
      setResult(prev => prev + `\n\n❌ ERROR: ${error.message}`);
      setResult(prev => prev + `\nError details: ${JSON.stringify(error)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">API Connection Test</h1>
        
        <button
          onClick={testAPI}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-6 py-3 rounded-lg font-semibold mb-8"
        >
          {loading ? 'Testing...' : 'Test API Connection'}
        </button>
        
        {result && (
          <div className="bg-gray-800 rounded-lg p-6">
            <pre className="whitespace-pre-wrap text-sm">{result}</pre>
          </div>
        )}
        
        <div className="mt-8 text-sm text-gray-400">
          <p>This page tests the connection to the FastAPI backend.</p>
          <p className="mt-2">Expected API URL: http://localhost:8000</p>
          <p className="mt-2">Make sure FastAPI is running: <code className="bg-gray-800 px-2 py-1 rounded">uvicorn backend.api.app:app --reload --port 8000</code></p>
        </div>
      </div>
    </div>
  );
}

