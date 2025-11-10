import React, { useState, useEffect, useCallback } from 'react';

const YouTubeDownloader = () => {
  const [url, setUrl] = useState('');
  const [format, setFormat] = useState('mp4');
  const [loading, setLoading] = useState(false);
  const [videoInfo, setVideoInfo] = useState(null);
  const [downloadStatus, setDownloadStatus] = useState(null);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [downloadHistory, setDownloadHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('download'); // 'download' or 'history'

  const API_BASE = 'http://localhost:8000/api';

  // Wrap fetchVideoInfo in useCallback to prevent unnecessary recreations
  const fetchVideoInfo = useCallback(async () => {
    if (!url) return;
    
    try {
      setError('');
      const response = await fetch(`${API_BASE}/video-info/?url=${encodeURIComponent(url)}`);
      const data = await response.json();
      
      if (response.ok) {
        setVideoInfo(data);
      } else {
        setError(data.error || 'Failed to fetch video info');
        setVideoInfo(null);
      }
    } catch (err) {
      setError('Failed to connect to server');
      setVideoInfo(null);
    }
  }, [url, API_BASE]);

  const fetchDownloadHistory = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/downloads/history/`);
      if (response.ok) {
        const data = await response.json();
        setDownloadHistory(data);
      }
    } catch (err) {
      console.error('Failed to fetch download history', err);
    }
  }, [API_BASE]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      if (url.includes('youtube.com') || url.includes('youtu.be')) {
        fetchVideoInfo();
      }
    }, 1000);

    return () => clearTimeout(delayDebounceFn);
  }, [url, fetchVideoInfo]);

  useEffect(() => {
    if (activeTab === 'history') {
      fetchDownloadHistory();
    }
  }, [activeTab, fetchDownloadHistory]);

  const startDownload = async () => {
    if (!url) {
      setError('Please enter a YouTube URL');
      return;
    }

    setLoading(true);
    setError('');
    setDownloadStatus('starting');
    setProgress(0);

    try {
      const response = await fetch(`${API_BASE}/download/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, format }),
      });

      const data = await response.json();

      if (response.ok) {
        setDownloadStatus('processing');
        // Start continuous polling for progress
        pollDownloadStatus(data.request_id);
      } else {
        setError(data.error || 'Failed to start download');
        setLoading(false);
      }
    } catch (err) {
      setError('Failed to connect to server');
      setLoading(false);
    }
  };

  const pollDownloadStatus = async (id) => {
    let pollCount = 0;
    const maxPolls = 300; // Maximum 15 minutes (300 * 3 seconds)
    
    const poll = async () => {
      if (pollCount >= maxPolls) {
        setError('Download timeout. Please try again.');
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/status/${id}/`);
        const data = await response.json();

        console.log('Progress update:', data.progress);

        // Update progress regardless of status
        if (data.progress !== undefined) {
          setProgress(Math.round(data.progress));
        }

        if (data.status === 'completed') {
          setDownloadStatus('completed');
          setProgress(100);
          setLoading(false);
          // Refresh download history
          fetchDownloadHistory();
          // Switch to history tab
          setActiveTab('history');
        } else if (data.status === 'failed') {
          setDownloadStatus('failed');
          setError('Download failed. Please try again.');
          setLoading(false);
          setProgress(0);
        } else {
          // Still processing, continue polling every 3 seconds
          pollCount++;
          setTimeout(poll, 3000);
        }
      } catch (err) {
        console.error('Polling error:', err);
        setError('Failed to check download status');
        setLoading(false);
      }
    };

    poll();
  };

  const deleteDownload = async (downloadId, fileName) => {
    if (window.confirm(`Are you sure you want to delete "${fileName}"?`)) {
      try {
        const response = await fetch(`${API_BASE}/downloads/delete/${downloadId}/`, {
          method: 'DELETE',
        });

        if (response.ok) {
          // Remove from local state
          setDownloadHistory(downloadHistory.filter(item => item.id !== downloadId));
        } else {
          const data = await response.json();
          setError(data.error || 'Failed to delete file');
        }
      } catch (err) {
        setError('Failed to delete file');
      }
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  // Progress bar component
  const ProgressBar = ({ progress, status }) => {
    return (
      <div style={{
        width: '100%',
        backgroundColor: '#e0e0e0',
        borderRadius: '10px',
        overflow: 'hidden',
        margin: '10px 0',
        height: '20px',
        position: 'relative'
      }}>
        <div
          style={{
            width: `${progress}%`,
            backgroundColor: 
              status === 'completed' ? '#4CAF50' :
              status === 'failed' ? '#f44336' :
              '#2196F3',
            height: '100%',
            borderRadius: '10px',
            transition: 'width 0.5s ease-in-out',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: '12px',
            fontWeight: 'bold'
          }}
        >
          {progress}%
        </div>
      </div>
    );
  };

  const DownloadItem = ({ download }) => {
    const isVideo = download.format === 'mp4';
    const isAudio = download.format === 'mp3';

    return (
      <div style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '15px',
        marginBottom: '15px',
        backgroundColor: 'white'
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '15px' }}>
          {download.thumbnail && (
            <img 
              src={download.thumbnail} 
              alt="Thumbnail"
              style={{
                width: '120px',
                height: '90px',
                borderRadius: '5px',
                objectFit: 'cover'
              }}
            />
          )}
          <div style={{ flex: 1 }}>
            <h4 style={{ margin: '0 0 10px 0', color: '#333' }}>
              {download.title}
            </h4>
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '10px' }}>
              <div>Format: {download.format.toUpperCase()}</div>
              <div>Size: {formatFileSize(download.file_size)}</div>
              {download.duration > 0 && <div>Duration: {formatDuration(download.duration)}</div>}
              <div>Downloaded: {formatDate(download.created_at)}</div>
            </div>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {isVideo && (
                <button
                  onClick={() => window.open(`${API_BASE}/play-file/?path=${encodeURIComponent(download.file_path)}`, '_blank')}
                  style={{
                    padding: '8px 15px',
                    backgroundColor: '#2196F3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  ▶ Play
                </button>
              )}
              {isAudio && (
                <button
                  onClick={() => {
                    const audio = new Audio(`${API_BASE}/play-file/?path=${encodeURIComponent(download.file_path)}`);
                    audio.play();
                  }}
                  style={{
                    padding: '8px 15px',
                    backgroundColor: '#2196F3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  🔈 Play
                </button>
              )}
              <button
                onClick={() => window.open(`${API_BASE}/download-file/?path=${encodeURIComponent(download.file_path)}`, '_blank')}
                style={{
                  padding: '8px 15px',
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                ⬇ Download
              </button>
              <button
                onClick={() => deleteDownload(download.id, download.file_name)}
                style={{
                  padding: '8px 15px',
                  backgroundColor: '#f44336',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                🗑 Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ 
      maxWidth: '800px', 
      margin: '20px auto', 
      padding: '20px',
      fontFamily: 'Arial, sans-serif',
      backgroundColor: '#f5f5f5',
      borderRadius: '10px',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
    }}>
      <h1 style={{ 
        textAlign: 'center', 
        color: '#333',
        marginBottom: '30px'
      }}>
        YouTube Downloader
      </h1>

      {/* Tab Navigation */}
      <div style={{ 
        display: 'flex', 
        marginBottom: '20px',
        borderBottom: '2px solid #ddd'
      }}>
        <button
          onClick={() => setActiveTab('download')}
          style={{
            padding: '10px 20px',
            backgroundColor: activeTab === 'download' ? '#ff4444' : 'transparent',
            color: activeTab === 'download' ? 'white' : '#666',
            border: 'none',
            borderBottom: activeTab === 'download' ? '2px solid #ff4444' : 'none',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          Download
        </button>
        <button
          onClick={() => setActiveTab('history')}
          style={{
            padding: '10px 20px',
            backgroundColor: activeTab === 'history' ? '#2196F3' : 'transparent',
            color: activeTab === 'history' ? 'white' : '#666',
            border: 'none',
            borderBottom: activeTab === 'history' ? '2px solid #2196F3' : 'none',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          Download History ({downloadHistory.length})
        </button>
      </div>

      {activeTab === 'download' && (
        <div>
          <div style={{ marginBottom: '20px' }}>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Enter YouTube URL"
              style={{
                width: '100%',
                padding: '12px',
                fontSize: '16px',
                border: '1px solid #ddd',
                borderRadius: '5px',
                marginBottom: '10px'
              }}
            />
            
            <div style={{ marginBottom: '15px' }}>
              <label style={{ marginRight: '15px' }}>
                <input
                  type="radio"
                  value="mp4"
                  checked={format === 'mp4'}
                  onChange={(e) => setFormat(e.target.value)}
                  style={{ marginRight: '5px' }}
                />
                MP4 (Video)
              </label>
              <label>
                <input
                  type="radio"
                  value="mp3"
                  checked={format === 'mp3'}
                  onChange={(e) => setFormat(e.target.value)}
                  style={{ marginRight: '5px' }}
                />
                MP3 (Audio)
              </label>
            </div>

            <button
              onClick={startDownload}
              disabled={loading || !url}
              style={{
                width: '100%',
                padding: '12px',
                fontSize: '16px',
                backgroundColor: loading ? '#ccc' : '#ff4444',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: loading ? 'not-allowed' : 'pointer',
                marginBottom: '10px'
              }}
            >
              {loading ? 'Downloading...' : 'Download'}
            </button>

            {/* Progress Bar */}
            {(downloadStatus === 'processing' || progress > 0) && (
              <div>
                <ProgressBar progress={progress} status={downloadStatus} />
                <div style={{
                  textAlign: 'center',
                  fontSize: '14px',
                  color: '#666',
                  marginBottom: '10px'
                }}>
                  {downloadStatus === 'completed' ? 'Download Complete!' : `Downloading... ${progress}%`}
                </div>
              </div>
            )}
          </div>

          {error && (
            <div style={{
              padding: '10px',
              backgroundColor: '#ffebee',
              color: '#c62828',
              borderRadius: '5px',
              marginBottom: '15px',
              border: '1px solid #ffcdd2'
            }}>
              {error}
            </div>
          )}

          {downloadStatus && downloadStatus !== 'processing' && downloadStatus !== 'completed' && (
            <div style={{
              padding: '10px',
              backgroundColor: '#fff3e0',
              color: '#f57c00',
              borderRadius: '5px',
              marginBottom: '15px',
              textAlign: 'center',
              border: '1px solid #ffe0b2'
            }}>
              {downloadStatus === 'starting' && 'Starting download...'}
              {downloadStatus === 'failed' && 'Download failed!'}
            </div>
          )}

          {videoInfo && (
            <div style={{
              padding: '15px',
              backgroundColor: 'white',
              borderRadius: '5px',
              border: '1px solid #ddd'
            }}>
              <h3 style={{ marginTop: 0, color: '#333' }}>Video Info</h3>
              {videoInfo.thumbnail && (
                <img 
                  src={videoInfo.thumbnail} 
                  alt="Thumbnail"
                  style={{
                    maxWidth: '100%',
                    height: 'auto',
                    borderRadius: '5px',
                    marginBottom: '10px'
                  }}
                />
              )}
              <p><strong>Title:</strong> {videoInfo.title}</p>
              <p><strong>Uploader:</strong> {videoInfo.uploader}</p>
              <p><strong>Duration:</strong> {formatDuration(videoInfo.duration)}</p>
              <p><strong>Available formats:</strong> {videoInfo.formats}</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'history' && (
        <div>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '15px'
          }}>
            <h3 style={{ margin: 0, color: '#333' }}>Downloaded Files</h3>
            <button
              onClick={fetchDownloadHistory}
              style={{
                padding: '8px 15px',
                backgroundColor: '#2196F3',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer'
              }}
            >
              🔄 Refresh
            </button>
          </div>

          {downloadHistory.length === 0 ? (
            <div style={{
              padding: '40px',
              textAlign: 'center',
              backgroundColor: 'white',
              borderRadius: '5px',
              border: '1px solid #ddd',
              color: '#666'
            }}>
              No downloads yet. Start by downloading a video!
            </div>
          ) : (
            <div>
              {downloadHistory.map(download => (
                <DownloadItem key={download.id} download={download} />
              ))}
            </div>
          )}
        </div>
      )}

      <div style={{ 
        marginTop: '20px', 
        fontSize: '12px', 
        color: '#666',
        textAlign: 'center'
      }}>
        <p>Note: This tool is for educational purposes only.</p>
        <p>Please respect copyright laws and YouTube's terms of service.</p>
      </div>
    </div>
  );
};

export default YouTubeDownloader;