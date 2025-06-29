import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Swipeable Card Component
const SwipeableCard = ({ content, contentType, onSwipe, currentIndex }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setStartPos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    
    const deltaX = e.clientX - startPos.x;
    const deltaY = e.clientY - startPos.y;
    setDragOffset({ x: deltaX, y: deltaY });
  };

  const handleMouseUp = () => {
    if (!isDragging) return;
    
    const threshold = 100;
    if (Math.abs(dragOffset.x) > threshold) {
      const action = dragOffset.x > 0 ? 'like' : 'dislike';
      onSwipe(content.id, action);
    }
    
    setIsDragging(false);
    setDragOffset({ x: 0, y: 0 });
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset, startPos]);

  const title = contentType === 'movie' ? content.title : content.name;
  const releaseDate = contentType === 'movie' ? content.release_date : content.first_air_date;
  const rotation = isDragging ? dragOffset.x * 0.1 : 0;
  const opacity = isDragging ? Math.max(0.7, 1 - Math.abs(dragOffset.x) / 300) : 1;

  return (
    <div 
      className={`swipeable-card ${isDragging ? 'dragging' : ''}`}
      style={{
        transform: `translate(${dragOffset.x}px, ${dragOffset.y}px) rotate(${rotation}deg)`,
        opacity: opacity,
        zIndex: 1000 - currentIndex
      }}
      onMouseDown={handleMouseDown}
    >
      <div className="card-content">
        {content.poster_url && (
          <div className="poster-container">
            <img 
              src={content.poster_url} 
              alt={title}
              className="poster-image"
              draggable={false}
            />
            <div className="card-overlay">
              <div className="rating">
                <span className="star">⭐</span>
                <span>{content.vote_average.toFixed(1)}</span>
              </div>
            </div>
          </div>
        )}
        <div className="card-info">
          <h3 className="card-title">{title}</h3>
          <p className="release-date">{new Date(releaseDate).getFullYear()}</p>
          <p className="overview">{content.overview}</p>
        </div>
      </div>
      
      {/* Swipe indicators */}
      {isDragging && (
        <>
          <div className={`swipe-indicator like ${dragOffset.x > 50 ? 'active' : ''}`}>
            LIKE
          </div>
          <div className={`swipe-indicator dislike ${dragOffset.x < -50 ? 'active' : ''}`}>
            PASS
          </div>
        </>
      )}
    </div>
  );
};

// Genre Filter Component
const GenreFilter = ({ genres, selectedGenres, onGenreToggle }) => {
  return (
    <div className="genre-filter">
      <h4>Filter by Genre:</h4>
      <div className="genre-buttons">
        {genres.map(genre => (
          <button
            key={genre.id}
            className={`genre-btn ${selectedGenres.includes(genre.id) ? 'active' : ''}`}
            onClick={() => onGenreToggle(genre.id)}
          >
            {genre.name}
          </button>
        ))}
      </div>
    </div>
  );
};

// Stats Component
const StatsPanel = ({ stats, onClose }) => {
  return (
    <div className="stats-panel">
      <div className="stats-content">
        <h3>Your Stats</h3>
        <div className="stats-grid">
          <div className="stat-item">
            <div className="stat-number">{stats.total_swipes}</div>
            <div className="stat-label">Total Swipes</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">{stats.liked_count}</div>
            <div className="stat-label">Liked</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">{stats.watching_count}</div>
            <div className="stat-label">Currently Watching</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">{stats.completed_count}</div>
            <div className="stat-label">Completed</div>
          </div>
        </div>
        <button className="close-btn" onClick={onClose}>Close</button>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [content, setContent] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [contentType, setContentType] = useState('movie');
  const [genres, setGenres] = useState([]);
  const [selectedGenres, setSelectedGenres] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [stats, setStats] = useState({});
  const [showGenreFilter, setShowGenreFilter] = useState(false);

  useEffect(() => {
    loadGenres();
    loadContent();
    loadStats();
  }, [contentType]);

  useEffect(() => {
    if (selectedGenres.length > 0) {
      loadContent();
    }
  }, [selectedGenres]);

  const loadGenres = async () => {
    try {
      const endpoint = contentType === 'movie' ? '/genres/movies' : '/genres/tv';
      const response = await axios.get(`${API}${endpoint}`);
      setGenres(response.data.genres);
    } catch (error) {
      console.error('Error loading genres:', error);
    }
  };

  const loadContent = async (page = 1) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/discover`, {
        content_type: contentType,
        genre_ids: selectedGenres.length > 0 ? selectedGenres : null,
        page: page
      });
      
      if (page === 1) {
        setContent(response.data.results);
        setCurrentIndex(0);
      } else {
        setContent(prev => [...prev, ...response.data.results]);
      }
    } catch (error) {
      console.error('Error loading content:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API}/stats/default_user`);
      setStats(response.data.stats);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleSwipe = async (contentId, action) => {
    try {
      await axios.post(`${API}/swipe`, {
        content_id: contentId,
        content_type: contentType,
        action: action,
        user_id: 'default_user'
      });
      
      setCurrentIndex(prev => prev + 1);
      loadStats(); // Update stats after swipe
      
      // Load more content if running low
      if (currentIndex >= content.length - 3) {
        const nextPage = Math.floor(currentIndex / 20) + 2;
        loadContent(nextPage);
      }
    } catch (error) {
      console.error('Error recording swipe:', error);
    }
  };

  const handleGenreToggle = (genreId) => {
    setSelectedGenres(prev => 
      prev.includes(genreId)
        ? prev.filter(id => id !== genreId)
        : [...prev, genreId]
    );
  };

  const currentContent = content[currentIndex];
  const nextContent = content[currentIndex + 1];

  return (
    <div className="App">
      <div className="app-header">
        <h1>🎬 MovieMatch</h1>
        <p>Discover your next favorite {contentType === 'movie' ? 'movie' : 'TV show'}</p>
      </div>

      <div className="content-type-toggle">
        <button 
          className={contentType === 'movie' ? 'active' : ''}
          onClick={() => setContentType('movie')}
        >
          🎬 Movies
        </button>
        <button 
          className={contentType === 'tv' ? 'active' : ''}
          onClick={() => setContentType('tv')}
        >
          📺 TV Shows
        </button>
      </div>

      <div className="app-controls">
        <button 
          className="control-btn filter-btn"
          onClick={() => setShowGenreFilter(!showGenreFilter)}
        >
          🎭 Genres
        </button>
        <button 
          className="control-btn stats-btn"
          onClick={() => setShowStats(true)}
        >
          📊 Stats
        </button>
      </div>

      {showGenreFilter && (
        <GenreFilter
          genres={genres}
          selectedGenres={selectedGenres}
          onGenreToggle={handleGenreToggle}
        />
      )}

      <div className="card-container">
        {loading && currentIndex === 0 ? (
          <div className="loading">
            <div className="loading-spinner"></div>
            <p>Loading amazing content...</p>
          </div>
        ) : (
          <>
            {/* Show next card behind current card */}
            {nextContent && (
              <SwipeableCard
                key={`${nextContent.id}-next`}
                content={nextContent}
                contentType={contentType}
                onSwipe={() => {}}
                currentIndex={1}
              />
            )}
            
            {/* Current card */}
            {currentContent ? (
              <SwipeableCard
                key={currentContent.id}
                content={currentContent}
                contentType={contentType}
                onSwipe={handleSwipe}
                currentIndex={0}
              />
            ) : (
              <div className="no-content">
                <h3>🎉 You've seen it all!</h3>
                <p>Try changing your genre filters or switch between movies and TV shows</p>
                <button onClick={() => loadContent(1)} className="reload-btn">
                  Load More Content
                </button>
              </div>
            )}
          </>
        )}
      </div>

      <div className="action-buttons">
        <button 
          className="action-btn dislike-btn"
          onClick={() => currentContent && handleSwipe(currentContent.id, 'dislike')}
          disabled={!currentContent}
        >
          👎 Pass
        </button>
        <button 
          className="action-btn like-btn"
          onClick={() => currentContent && handleSwipe(currentContent.id, 'like')}
          disabled={!currentContent}
        >
          👍 Like
        </button>
      </div>

      {showStats && (
        <StatsPanel
          stats={stats}
          onClose={() => setShowStats(false)}
        />
      )}
    </div>
  );
}

export default App;