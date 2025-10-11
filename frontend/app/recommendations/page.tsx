/**
 * Recommendations Page - Get personalized movie recommendations
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { getRecommendations, type RecommendationsResponse } from '@/lib/api';

const SAMPLE_USERS = [
  { name: 'Ned Stark', email: 'sean_bean@gameofthron.es' },
  { name: 'Robert Baratheon', email: 'mark_addy@gameofthron.es' },
  { name: 'Daenerys Targaryen', email: 'emilia_clarke@gameofthron.es' },
];

export default function RecommendationsPage() {
  const [email, setEmail] = useState('mark_addy@gameofthron.es');
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  async function handleGetRecommendations() {
    if (!email) {
      setError('Please enter an email address');
      return;
    }

    try {
      setLoading(true);
      setError('');
      const data = await getRecommendations(email, 5);
      setRecommendations(data);
    } catch (err) {
      setError('Failed to load recommendations. Make sure the user exists and the API is running.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <Link href="/" className="text-3xl font-bold hover:text-blue-400 transition">
              🎬 ContextScope Movies
            </Link>
            <div className="text-sm text-gray-400">
              Powered by Multi-Agent AI Pipeline
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-4xl font-bold mb-8">Get Personalized Recommendations</h1>

        {/* User Input */}
        <div className="bg-gray-800 rounded-lg p-6 mb-8">
          <label htmlFor="email" className="block text-sm font-medium mb-4">
            Select a User or Enter Email
          </label>
          
          {/* Quick Select Users */}
          <div className="flex flex-wrap gap-2 mb-4">
            {SAMPLE_USERS.map((user) => (
              <button
                key={user.email}
                onClick={() => setEmail(user.email)}
                className={`px-4 py-2 rounded-lg transition ${
                  email === user.email
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {user.name}
              </button>
            ))}
          </div>

          <div className="flex gap-4">
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyPress={(e) => e.key === 'Enter' && handleGetRecommendations()}
            />
            <button
              onClick={handleGetRecommendations}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-8 py-2 rounded-lg font-semibold transition"
            >
              {loading ? 'Loading...' : 'Get Recommendations'}
            </button>
          </div>
          <p className="text-sm text-gray-400 mt-2">
            Each user gets personalized recommendations based on their viewing history
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded mb-8">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            <p className="mt-4 text-gray-400">Running AI pipeline...</p>
            <p className="text-sm text-gray-500 mt-2">
              User Profiler → Content Analyzer → Recommender → Explainer
            </p>
          </div>
        )}

        {/* Recommendations */}
        {recommendations && !loading && (
          <div className="space-y-8">
            {/* User Info */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-2xl font-bold mb-2">
                Recommendations for {recommendations.user.name}
              </h2>
              <p className="text-gray-400">{recommendations.user.email}</p>
            </div>

            {/* Movies */}
            <div className="space-y-6">
              {recommendations.recommendations.map((rec) => (
                <div
                  key={rec.rank}
                  className="bg-gray-800 rounded-lg p-6 hover:ring-2 hover:ring-blue-500 transition"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="bg-blue-600 text-white w-8 h-8 rounded-full flex items-center justify-center font-bold">
                          {rec.rank}
                        </span>
                        <h3 className="text-2xl font-bold">
                          {rec.title}
                        </h3>
                        <span className="text-gray-400">({rec.year})</span>
                      </div>
                    </div>
                    {rec.imdb_rating && (
                      <div className="text-right">
                        <div className="text-2xl font-bold text-yellow-400">
                          ★ {rec.imdb_rating}
                        </div>
                        <div className="text-sm text-gray-400">IMDb</div>
                      </div>
                    )}
                  </div>

                  {/* Genres */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {rec.genres.map((genre) => (
                      <span
                        key={genre}
                        className="bg-gray-700 px-3 py-1 rounded-full text-sm"
                      >
                        {genre}
                      </span>
                    ))}
                  </div>

                  {/* Confidence */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-gray-400">Match Confidence</span>
                      <span className="font-semibold">{Math.round(rec.confidence * 100)}%</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{ width: `${rec.confidence * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Explanation */}
                  <div className="bg-gray-700 rounded-lg p-4 mb-4">
                    <p className="text-gray-200">{rec.explanation}</p>
                  </div>

                  {/* Key Points */}
                  {rec.key_appeal_points.length > 0 && (
                    <div>
                      <h4 className="font-semibold mb-2">Why you'll love it:</h4>
                      <ul className="space-y-1">
                        {rec.key_appeal_points.map((point, idx) => (
                          <li key={idx} className="text-gray-400 text-sm">
                            • {point}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Pipeline Metrics */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-xl font-bold mb-4">Pipeline Performance</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-2xl font-bold text-blue-400">
                    {Math.round(recommendations.pipeline_metrics.total_execution_time_ms)}ms
                  </div>
                  <div className="text-sm text-gray-400">Total Time</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-400">
                    {recommendations.pipeline_metrics.agents.content_analyzer.candidates_found}
                  </div>
                  <div className="text-sm text-gray-400">Candidates Analyzed</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-purple-400">
                    {recommendations.recommendations.length}
                  </div>
                  <div className="text-sm text-gray-400">Recommendations</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-yellow-400">4</div>
                  <div className="text-sm text-gray-400">AI Agents</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

