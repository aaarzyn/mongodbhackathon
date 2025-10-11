/**
 * Homepage - Movie Catalog
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getTopRatedMovies, getGenres, getMovies, type Movie } from '@/lib/api';

export default function Home() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [genres, setGenres] = useState<string[]>([]);
  const [selectedGenre, setSelectedGenre] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [isClient, setIsClient] = useState(false);

  // Ensure we're only running on the client
  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient) return;
    
    loadGenres();
    loadMovies();
  }, [isClient]);

  useEffect(() => {
    if (!isClient) return;
    
    if (selectedGenre) {
      loadMoviesByGenre(selectedGenre);
    } else {
      loadMovies();
    }
  }, [selectedGenre, isClient]);

  async function loadGenres() {
    try {
      const data = await getGenres();
      setGenres(data);
    } catch (err) {
      console.error('Failed to load genres:', err);
    }
  }

  async function loadMovies() {
    try {
      setLoading(true);
      setError('');
      console.log('Loading top-rated movies...');
      const data = await getTopRatedMovies(24);
      console.log('Received movies:', data.length);
      setMovies(data);
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to load movies. Make sure the API is running on port 8000.';
      setError(errorMsg);
      console.error('loadMovies error:', err);
    } finally {
      setLoading(false);
    }
  }

  async function loadMoviesByGenre(genre: string) {
    try {
      setLoading(true);
      setError('');
      console.log('Loading movies for genre:', genre);
      const data = await getMovies({ genre, limit: 24 });
      console.log('Received movies:', data.length);
      setMovies(data);
    } catch (err: any) {
      const errorMsg = err?.message || `Failed to load ${genre} movies. Make sure the API is running.`;
      setError(errorMsg);
      console.error('loadMoviesByGenre error:', err);
    } finally {
      setLoading(false);
    }
  }

  // Don't render until we're on the client
  if (!isClient) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold">
              🎬 ContextScope Movies
            </h1>
            <Link
              href="/recommendations"
              className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg font-semibold transition"
            >
              Get Recommendations
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Genre Filter */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Filter by Genre</h2>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedGenre('')}
              className={`px-4 py-2 rounded-full transition ${
                selectedGenre === ''
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              All Movies
            </button>
            {genres.map((genre) => (
              <button
                key={genre}
                onClick={() => setSelectedGenre(genre)}
                className={`px-4 py-2 rounded-full transition ${
                  selectedGenre === genre
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {genre}
              </button>
            ))}
          </div>
          <p className="text-sm text-gray-400 mt-2">
            Showing {genres.length} genres • Try: Action, Fantasy, Western
          </p>
        </div>

        {/* Movie Grid */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            <p className="mt-4 text-gray-400">Loading movies...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {!loading && !error && movies.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-400 text-lg">No movies found</p>
            <p className="text-gray-500 text-sm mt-2">Try selecting a different genre or check if the API is running</p>
          </div>
        )}

        {!loading && !error && movies.length > 0 && (
          <>
            <h2 className="text-2xl font-bold mb-6">
              {selectedGenre ? `${selectedGenre} Movies` : 'Top Rated Movies'}
              <span className="text-gray-400 text-lg ml-3">({movies.length} movies)</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {movies.map((movie, idx) => {
                // Handle both nested and flat rating structure
                const rating = movie.imdb?.rating || movie.imdb_rating;
                
                // Skip movies without essential data
                if (!movie.title) {
                  return null;
                }
                
                return (
                  <div
                    key={movie._id || movie.id || `movie-${idx}`}
                    className="bg-gray-800 rounded-lg overflow-hidden hover:ring-2 hover:ring-blue-500 transition relative"
                  >
                    {/* Embedding Badge */}
                    {movie.plot_embedding_available && (
                      <div className="absolute top-2 right-2 bg-blue-600 text-white text-xs px-2 py-1 rounded-full font-semibold">
                        🧠 AI
                      </div>
                    )}
                    
                    <div className="p-4">
                      <h3 className="font-bold text-lg mb-2 line-clamp-2">
                        {movie.title}
                      </h3>
                      <div className="space-y-2 text-sm text-gray-400">
                        {movie.year && <p>Year: {movie.year}</p>}
                        {rating && (
                          <p className="flex items-center">
                            <span className="text-yellow-400 mr-1">★</span>
                            {rating}/10
                          </p>
                        )}
                        {movie.genres && movie.genres.length > 0 && (
                          <p className="text-gray-500">
                            {movie.genres.slice(0, 3).join(', ')}
                          </p>
                        )}
                        {movie.directors && movie.directors.length > 0 && (
                          <p className="text-gray-500">
                            Dir: {movie.directors[0]}
                          </p>
                        )}
                        {movie.plot_embedding_available && (
                          <p className="text-blue-400 text-xs mt-2">
                            ✓ Has AI embeddings
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
