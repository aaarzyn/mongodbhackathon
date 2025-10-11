/**
 * Modal to display embedding information for movies
 */

'use client';

import { Movie } from '@/lib/api';

interface EmbeddingModalProps {
  movie: Movie | null;
  onClose: () => void;
}

export default function EmbeddingModal({ movie, onClose }: EmbeddingModalProps) {
  if (!movie) return null;

  const hasPlotEmbedding = movie.plot_embedding_available;
  const hasVoyageEmbedding = movie.plot_embedding_voyage_3_large_available;

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div 
        className="bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="border-b border-gray-700 p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-2xl font-bold mb-2">{movie.title}</h2>
              <p className="text-gray-400">{movie.year} • {movie.genres?.join(', ')}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white text-2xl leading-none"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* AI Embedding Badge */}
          <div className="bg-blue-900 border border-blue-700 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-3xl">🧠</span>
              <div>
                <h3 className="text-lg font-bold text-blue-300">AI Embeddings Available</h3>
                <p className="text-sm text-blue-200">
                  This movie has semantic embeddings for context evaluation
                </p>
              </div>
            </div>
          </div>

          {/* Movie Details */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Movie Details</h3>
            <div className="bg-gray-700 rounded-lg p-4 space-y-2">
              {movie.imdb?.rating && (
                <div className="flex justify-between">
                  <span className="text-gray-400">IMDb Rating:</span>
                  <span className="font-semibold text-yellow-400">
                    ★ {movie.imdb.rating}/10
                  </span>
                </div>
              )}
              {movie.imdb?.votes && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Votes:</span>
                  <span>{movie.imdb.votes.toLocaleString()}</span>
                </div>
              )}
              {movie.directors && movie.directors.length > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Director:</span>
                  <span>{movie.directors.slice(0, 2).join(', ')}</span>
                </div>
              )}
              {movie.runtime && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Runtime:</span>
                  <span>{movie.runtime} minutes</span>
                </div>
              )}
              {movie.rated && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Rated:</span>
                  <span>{movie.rated}</span>
                </div>
              )}
            </div>
          </div>

          {/* Plot */}
          {movie.plot && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Plot</h3>
              <p className="text-gray-300 leading-relaxed">{movie.plot}</p>
            </div>
          )}

          {/* Embedding Information */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Embedding Information</h3>
            <div className="space-y-3">
              {/* Plot Embedding */}
              {hasPlotEmbedding && (
                <div className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-green-400">✓</span>
                    <span className="font-semibold">plot_embedding</span>
                  </div>
                  <div className="text-sm text-gray-400 space-y-1">
                    <p>• Standard plot embedding vector</p>
                    <p>• Used for semantic similarity search</p>
                    <p>• Powers content-based recommendations</p>
                    <p>• Enables context fidelity evaluation</p>
                  </div>
                </div>
              )}

              {/* Voyage 3 Large Embedding */}
              {hasVoyageEmbedding && (
                <div className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-green-400">✓</span>
                    <span className="font-semibold">plot_embedding_voyage_3_large</span>
                  </div>
                  <div className="text-sm text-gray-400 space-y-1">
                    <p>• High-dimensional Voyage AI embedding</p>
                    <p>• Enhanced semantic understanding</p>
                    <p>• Better context transmission quality</p>
                  </div>
                </div>
              )}

              {!hasPlotEmbedding && !hasVoyageEmbedding && (
                <div className="bg-gray-700 rounded-lg p-4 text-gray-400">
                  <p>No embeddings available for this movie.</p>
                </div>
              )}
            </div>
          </div>

          {/* How Embeddings Are Used */}
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
            <h4 className="font-semibold mb-2 text-blue-300">
              How embeddings power ContextScope:
            </h4>
            <ul className="text-sm text-gray-400 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">→</span>
                <span><strong>Semantic Search:</strong> Find similar movies based on plot meaning</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">→</span>
                <span><strong>Context Evaluation:</strong> Measure information preservation in agent-to-agent communication</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">→</span>
                <span><strong>Fidelity Analysis:</strong> Track how well context survives through the pipeline</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">→</span>
                <span><strong>Drift Detection:</strong> Identify when recommendations lose relevance</span>
              </li>
            </ul>
          </div>

          {/* Genre Coverage Info */}
          {movie.genres && (
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
              <h4 className="font-semibold mb-2">Embedding Coverage by Genre:</h4>
              <div className="text-sm text-gray-400 space-y-1">
                {movie.genres.includes('Action') && <p>• Action: 100% coverage (2,381 movies)</p>}
                {movie.genres.includes('Fantasy') && <p>• Fantasy: 100% coverage (1,055 movies)</p>}
                {movie.genres.includes('Western') && <p>• Western: 100% coverage (242 movies)</p>}
                {movie.genres.includes('Sci-Fi') && <p>• Sci-Fi: 35.5% coverage (340 movies)</p>}
                {movie.genres.includes('Drama') && <p>• Drama: 10.3% coverage (1,271 movies)</p>}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-700 p-4 bg-gray-900">
          <button
            onClick={onClose}
            className="w-full bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg font-semibold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

