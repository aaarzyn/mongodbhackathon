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

  useEffect(() => {
    loadGenres();
    loadMovies();
  }, []);

  useEffect(() => {
    if (selectedGenre) {
      loadMoviesByGenre(selectedGenre);
    } else {
      loadMovies();
    }
  }, [selectedGenre]);

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
      const data = await getTopRatedMovies(24);
      setMovies(data);
      setError('');
    } catch (err) {
      setError('Failed to load movies');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function loadMoviesByGenre(genre: string) {
    try {
      setLoading(true);
      const data = await getMovies({ genre, limit: 24 });
      setMovies(data);
      setError('');
    } catch (err) {
      setError('Failed to load movies');
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
            {genres.slice(0, 10).map((genre) => (
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

        {!loading && !error && (
          <>
            <h2 className="text-2xl font-bold mb-6">
              {selectedGenre ? `${selectedGenre} Movies` : 'Top Rated Movies'}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {movies.map((movie, idx) => {
                const rating = movie.imdb?.rating || movie.imdb_rating;
                return (
                  <div
                    key={movie._id || movie.id || idx}
                    className="bg-gray-800 rounded-lg overflow-hidden hover:ring-2 hover:ring-blue-500 transition"
                  >
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
