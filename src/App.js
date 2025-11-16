import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Music, Video, Download, Trash2, Play, CheckCircle, XCircle, Loader, SkipBack, SkipForward, Volume2, VolumeX, Repeat, Shuffle, List, X } from 'lucide-react';

const YouTubeDownloader = () => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [downloadStatus, setDownloadStatus] = useState(null);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [downloadHistory, setDownloadHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('download');
  const [downloadMode, setDownloadMode] = useState(null);
  const [currentDownload, setCurrentDownload] = useState(null);
  const [historyFilter, setHistoryFilter] = useState('all');
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [deviceId, setDeviceId] = useState(null);
  
  // Media player states
  const [currentMedia, setCurrentMedia] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [repeatMode, setRepeatMode] = useState('off'); // 'off', 'one', 'all'
  const [shuffleMode, setShuffleMode] = useState(false);
  const [showPlaylist, setShowPlaylist] = useState(false);
  const [playlist, setPlaylist] = useState([]);
  const [currentPlaylistIndex, setCurrentPlaylistIndex] = useState(0);

  const audioRef = useRef(null);
  const videoRef = useRef(null);

  const API_BASE = 'https://youtubedownloder.207.180.201.93.sslip.io/api';

  // Define lineClamp styles as constants outside the styles object
  const lineClamp1 = {
    display: '-webkit-box',
    WebkitLineClamp: 1,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden'
  };

  const lineClamp2 = {
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden'
  };

  // Generate or retrieve device ID
  useEffect(() => {
    const generateDeviceId = () => {
      let deviceId = localStorage.getItem('youtube_downloader_device_id');
      if (!deviceId) {
        deviceId = 'device_' + Math.random().toString(36).substr(2, 9) + 
                   '_' + Date.now().toString(36);
        localStorage.setItem('youtube_downloader_device_id', deviceId);
        
        const deviceInfo = {
          userAgent: navigator.userAgent,
          language: navigator.language,
          platform: navigator.platform,
          timestamp: new Date().toISOString()
        };
        localStorage.setItem('device_info', JSON.stringify(deviceInfo));
      }
      setDeviceId(deviceId);
    };
    
    generateDeviceId();
  }, []);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Initialize playlist from download history when history changes
  useEffect(() => {
    if (downloadHistory.length > 0) {
      setPlaylist(downloadHistory);
    }
  }, [downloadHistory]);

  // Media player controls
  const togglePlayPause = () => {
    if (currentMedia) {
      if (currentMedia.format === 'mp3') {
        if (isPlaying) {
          audioRef.current.pause();
        } else {
          audioRef.current.play();
        }
      } else {
        if (isPlaying) {
          videoRef.current.pause();
        } else {
          videoRef.current.play();
        }
      }
      setIsPlaying(!isPlaying);
    }
  };

  const playMedia = (media, index = 0) => {
    setCurrentMedia(media);
    setCurrentPlaylistIndex(index);
    setIsPlaying(true);
    
    // Auto-play after a short delay to ensure ref is set
    setTimeout(() => {
      if (media.format === 'mp3' && audioRef.current) {
        audioRef.current.play();
      } else if (videoRef.current) {
        videoRef.current.play();
      }
    }, 100);
  };

  const playNext = () => {
    if (playlist.length === 0) return;
    
    let nextIndex;
    if (shuffleMode) {
      nextIndex = Math.floor(Math.random() * playlist.length);
    } else {
      nextIndex = (currentPlaylistIndex + 1) % playlist.length;
    }
    
    if (repeatMode === 'one') {
      // Restart current media
      setCurrentTime(0);
      if (currentMedia.format === 'mp3' && audioRef.current) {
        audioRef.current.currentTime = 0;
        audioRef.current.play();
      } else if (videoRef.current) {
        videoRef.current.currentTime = 0;
        videoRef.current.play();
      }
    } else {
      playMedia(playlist[nextIndex], nextIndex);
    }
  };

  const playPrevious = () => {
    if (playlist.length === 0) return;
    
    let prevIndex;
    if (shuffleMode) {
      prevIndex = Math.floor(Math.random() * playlist.length);
    } else {
      prevIndex = (currentPlaylistIndex - 1 + playlist.length) % playlist.length;
    }
    
    playMedia(playlist[prevIndex], prevIndex);
  };

  const toggleRepeat = () => {
    const modes = ['off', 'one', 'all'];
    const currentIndex = modes.indexOf(repeatMode);
    setRepeatMode(modes[(currentIndex + 1) % modes.length]);
  };

  const toggleShuffle = () => {
    setShuffleMode(!shuffleMode);
  };

  const handleTimeUpdate = () => {
    if (currentMedia) {
      const mediaElement = currentMedia.format === 'mp3' ? audioRef.current : videoRef.current;
      if (mediaElement) {
        setCurrentTime(mediaElement.currentTime);
        setDuration(mediaElement.duration || 0);
      }
    }
  };

  const handleSeek = (e) => {
    const seekTime = parseFloat(e.target.value);
    setCurrentTime(seekTime);
    
    if (currentMedia) {
      const mediaElement = currentMedia.format === 'mp3' ? audioRef.current : videoRef.current;
      if (mediaElement) {
        mediaElement.currentTime = seekTime;
      }
    }
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
    
    if (audioRef.current) audioRef.current.volume = newVolume;
    if (videoRef.current) videoRef.current.volume = newVolume;
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (audioRef.current) audioRef.current.muted = !isMuted;
    if (videoRef.current) videoRef.current.muted = !isMuted;
  };

  const handleMediaEnd = () => {
    if (repeatMode === 'one') {
      // Restart current media
      setCurrentTime(0);
      if (currentMedia.format === 'mp3' && audioRef.current) {
        audioRef.current.currentTime = 0;
        audioRef.current.play();
      } else if (videoRef.current) {
        videoRef.current.currentTime = 0;
        videoRef.current.play();
      }
    } else if (repeatMode === 'all' || shuffleMode) {
      playNext();
    } else {
      setIsPlaying(false);
    }
  };

  // Filter history based on selected filter
  const filteredHistory = downloadHistory.filter(item => {
    if (historyFilter === 'all') return true;
    if (historyFilter === 'music') return item.format === 'mp3';
    if (historyFilter === 'videos') return item.format === 'mp4';
    return true;
  });

  const fetchDownloadHistory = useCallback(async () => {
    if (!deviceId) return;
    
    try {
      const response = await fetch(`${API_BASE}/downloads/history/?device_id=${encodeURIComponent(deviceId)}`);
      if (response.ok) {
        const data = await response.json();
        setDownloadHistory(data);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to fetch history');
      }
    } catch (err) {
      console.error('Failed to fetch download history', err);
      setError('Failed to connect to server');
    }
  }, [deviceId]);

  useEffect(() => {
    if (activeTab === 'history' && deviceId) {
      fetchDownloadHistory();
    }
  }, [activeTab, fetchDownloadHistory, deviceId]);

  const startDownload = async () => {
    if (!url) {
      setError('Please enter a YouTube URL');
      return;
    }

    if (!downloadMode) {
      setError('Please select download type (Music or Videos) first');
      return;
    }

    if (!deviceId) {
      setError('Device not initialized. Please refresh the page.');
      return;
    }

    const formatType = downloadMode === 'music' ? 'mp3' : 'mp4';

    setLoading(true);
    setError('');
    setDownloadStatus('starting');
    setProgress(0);
    setCurrentDownload({
      title: 'Downloading...',
      thumbnail: ''
    });

    try {
      const response = await fetch(`${API_BASE}/download/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          url: url, 
          format: formatType,
          device_id: deviceId
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setDownloadStatus('processing');
        pollDownloadStatus(data.request_id);
      } else {
        setError(data.error || 'Failed to start download');
        setLoading(false);
        setDownloadStatus(null);
      }
    } catch (err) {
      setError('Failed to connect to server');
      setLoading(false);
      setDownloadStatus(null);
    }
  };

  const pollDownloadStatus = async (id) => {
    let pollCount = 0;
    const maxPolls = 200;
    
    const poll = async () => {
      if (pollCount >= maxPolls) {
        setError('Download timeout. Please try again.');
        setLoading(false);
        setDownloadStatus(null);
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/status/${id}/`);
        const data = await response.json();

        if (data.progress !== undefined) {
          setProgress(Math.round(data.progress));
        }

        if (data.video_title && currentDownload) {
          setCurrentDownload(prev => ({
            ...prev,
            title: data.video_title
          }));
        }

        if (data.status === 'completed') {
          setDownloadStatus('completed');
          setProgress(100);
          setTimeout(() => {
            setLoading(false);
            fetchDownloadHistory();
            setActiveTab('history');
            setDownloadMode(null);
            setUrl('');
            setDownloadStatus(null);
            setCurrentDownload(null);
            setProgress(0);
          }, 1500);
        } else if (data.status === 'failed') {
          setDownloadStatus('failed');
          setError(data.error || 'Download failed. Please try again.');
          setLoading(false);
          setProgress(0);
        } else {
          pollCount++;
          setTimeout(poll, 1000);
        }
      } catch (err) {
        console.error('Polling error:', err);
        setError('Failed to check download status');
        setLoading(false);
        setDownloadStatus(null);
      }
    };

    poll();
  };

  const deleteDownload = async (downloadId, fileName) => {
    if (!deviceId) {
      setError('Device not initialized');
      return;
    }

    if (window.confirm(`Delete "${fileName}"?`)) {
      try {
        const response = await fetch(`${API_BASE}/downloads/delete/${downloadId}/?device_id=${encodeURIComponent(deviceId)}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          setDownloadHistory(downloadHistory.filter(item => item.id !== downloadId));
          // Also remove from playlist if it's there
          setPlaylist(playlist.filter(item => item.id !== downloadId));
          
          // If current media is deleted, stop playback
          if (currentMedia && currentMedia.id === downloadId) {
            setCurrentMedia(null);
            setIsPlaying(false);
          }
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

  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '0:00';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const styles = {
    container: {
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%)',
      padding: isMobile ? '0.5rem' : '1rem',
      paddingBottom: currentMedia ? (isMobile ? '120px' : '100px') : (isMobile ? '0.5rem' : '1rem')
    },
    wrapper: {
      maxWidth: '1200px',
      margin: '0 auto'
    },
    header: {
      textAlign: 'center',
      marginBottom: isMobile ? '1rem' : '2rem'
    },
    title: {
      fontSize: isMobile ? '1.5rem' : '2.25rem',
      fontWeight: 'bold',
      color: '#1f2937',
      marginBottom: '0.5rem'
    },
    subtitle: {
      color: '#6b7280',
      fontSize: isMobile ? '0.875rem' : '1rem'
    },
    tabContainer: {
      display: 'flex',
      gap: isMobile ? '0.5rem' : '1rem',
      marginBottom: '1.5rem'
    },
    tabButton: {
      flex: 1,
      padding: isMobile ? '0.5rem' : '0.75rem',
      borderRadius: '0.5rem',
      fontWeight: '600',
      transition: 'all 0.3s ease',
      border: 'none',
      cursor: 'pointer',
      fontSize: isMobile ? '0.875rem' : '1rem'
    },
    tabButtonActive: {
      background: 'linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)',
      color: 'white',
      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
    },
    tabButtonInactive: {
      backgroundColor: 'white',
      color: '#374151'
    },
    errorAlert: {
      backgroundColor: '#fef2f2',
      border: '1px solid #fecaca',
      color: '#991b1b',
      padding: '0.75rem 1rem',
      borderRadius: '0.5rem',
      marginBottom: '1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: isMobile ? '0.875rem' : '1rem'
    },
    card: {
      backgroundColor: 'white',
      borderRadius: '1rem',
      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
      padding: isMobile ? '1rem' : '1.5rem'
    },
    centerContent: {
      textAlign: 'center',
      padding: isMobile ? '1rem 0' : '2rem 0'
    },
    modeSelection: {
      display: 'flex',
      flexDirection: isMobile ? 'column' : 'row',
      gap: '1.5rem',
      justifyContent: 'center',
      marginTop: '1.5rem',
      alignItems: isMobile ? 'stretch' : 'center'
    },
    modeButton: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: '1rem',
      padding: isMobile ? '1.5rem' : '2rem',
      color: 'white',
      borderRadius: '1rem',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      width: isMobile ? '100%' : '12rem',
      border: 'none'
    },
    modeIndicator: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '1.5rem',
      padding: isMobile ? '0.75rem' : '1rem',
      background: 'linear-gradient(135deg, #0ecd74ff 0%, #e9d5ff 100%)',
      borderRadius: '0.5rem',
      flexDirection: isMobile ? 'column' : 'row',
      gap: isMobile ? '0.75rem' : '0'
    },
    input: {
      flex: 1,
      padding: isMobile ? '0.75rem' : '0.75rem 1rem',
      border: '1px solid #d1d5db',
      borderRadius: '0.5rem',
      outline: 'none',
      fontSize: isMobile ? '0.875rem' : '1rem',
      width: '100%',
      boxSizing: 'border-box'
    },
    button: {
      padding: isMobile ? '0.625rem 1rem' : '0.75rem 1.5rem',
      borderRadius: '0.5rem',
      border: 'none',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontWeight: '500',
      fontSize: isMobile ? '0.875rem' : '1rem'
    },
    buttonPrimary: {
      backgroundColor: '#2563eb',
      color: 'white'
    },
    buttonDisabled: {
      backgroundColor: '#9ca3af',
      cursor: 'not-allowed'
    },
    downloadButton: {
      width: '100%',
      padding: isMobile ? '0.875rem' : '1rem',
      borderRadius: '0.5rem',
      fontWeight: 'bold',
      fontSize: isMobile ? '1rem' : '1.125rem',
      border: 'none',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.5rem',
      transition: 'all 0.3s ease'
    },
    progressContainer: {
      marginTop: '1.5rem',
      padding: isMobile ? '0.75rem' : '1rem',
      backgroundColor: '#f9fafb',
      borderRadius: '0.5rem'
    },
    progressBar: {
      width: '100%',
      height: isMobile ? '1.75rem' : '2rem',
      backgroundColor: '#e5e7eb',
      borderRadius: '9999px',
      overflow: 'hidden',
      position: 'relative'
    },
    progressFill: {
      height: '100%',
      transition: 'all 0.3s ease',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'white',
      fontSize: isMobile ? '0.75rem' : '0.875rem',
      fontWeight: 'bold'
    },
    historyItem: {
      display: 'flex',
      gap: isMobile ? '0.75rem' : '1rem',
      padding: isMobile ? '0.75rem' : '1rem',
      backgroundColor: '#f9fafb',
      borderRadius: '0.5rem',
      marginBottom: '1rem',
      transition: 'all 0.3s ease',
      flexDirection: isMobile ? 'column' : 'row'
    },
    historyThumbnail: {
      width: isMobile ? '100%' : '10rem',
      height: isMobile ? 'auto' : '7rem',
      borderRadius: '0.5rem',
      objectFit: 'cover'
    },
    videoThumbnail: {
      width: isMobile ? '100%' : '8rem',
      height: isMobile ? 'auto' : '5rem',
      borderRadius: '0.25rem',
      objectFit: 'cover'
    },
    actionButtons: {
      display: 'flex',
      gap: '0.5rem',
      marginTop: '0.75rem',
      flexWrap: 'wrap'
    },
    footer: {
      textAlign: 'center',
      marginTop: '2rem',
      fontSize: isMobile ? '0.75rem' : '0.875rem',
      color: '#6b7280'
    },
    // Media player styles
    mediaPlayer: {
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      backgroundColor: 'white',
      borderTop: '1px solid #e5e7eb',
      padding: isMobile ? '0.75rem' : '1rem',
      boxShadow: '0 -4px 6px -1px rgba(0, 0, 0, 0.1)',
      zIndex: 1000
    },
    playerControls: {
      display: 'flex',
      alignItems: 'center',
      gap: isMobile ? '0.5rem' : '1rem',
      flexDirection: isMobile ? 'column' : 'row'
    },
    playerInfo: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      flex: 1,
      minWidth: 0
    },
    playerThumbnail: {
      width: isMobile ? '40px' : '50px',
      height: isMobile ? '40px' : '50px',
      borderRadius: '0.375rem',
      objectFit: 'cover'
    },
    playerText: {
      minWidth: 0,
      flex: 1
    },
    playerTitle: {
      fontWeight: '600',
      fontSize: isMobile ? '0.875rem' : '1rem',
      ...lineClamp1
    },
    playerSubtitle: {
      color: '#6b7280',
      fontSize: isMobile ? '0.75rem' : '0.875rem'
    },
    controlButtons: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem'
    },
    controlButton: {
      padding: isMobile ? '0.375rem' : '0.5rem',
      borderRadius: '50%',
      border: 'none',
      backgroundColor: '#f3f4f6',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    },
    playButton: {
      padding: isMobile ? '0.5rem' : '0.75rem',
      backgroundColor: '#2563eb',
      color: 'white'
    },
    progressSection: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      flex: 2,
      width: isMobile ? '100%' : 'auto'
    },
    timeDisplay: {
      fontSize: isMobile ? '0.75rem' : '0.875rem',
      color: '#6b7280',
      minWidth: '40px'
    },
    progressSlider: {
      flex: 1,
      height: '4px',
      borderRadius: '2px',
      backgroundColor: '#e5e7eb',
      outline: 'none',
      cursor: 'pointer'
    },
    volumeSection: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      flex: isMobile ? 1 : 'none'
    },
    volumeSlider: {
      width: isMobile ? '60px' : '80px',
      height: '4px',
      borderRadius: '2px',
      backgroundColor: '#e5e7eb',
      outline: 'none',
      cursor: 'pointer'
    },
    // Playlist styles
    playlistOverlay: {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      zIndex: 2000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: isMobile ? '1rem' : '2rem'
    },
    playlistModal: {
      backgroundColor: 'white',
      borderRadius: '1rem',
      width: '100%',
      maxWidth: '500px',
      maxHeight: '80vh',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column'
    },
    playlistHeader: {
      padding: '1rem 1.5rem',
      borderBottom: '1px solid #e5e7eb',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    },
    playlistTitle: {
      fontWeight: 'bold',
      fontSize: '1.25rem'
    },
    playlistClose: {
      padding: '0.5rem',
      borderRadius: '0.375rem',
      border: 'none',
      backgroundColor: '#f3f4f6',
      cursor: 'pointer'
    },
    playlistContent: {
      flex: 1,
      overflow: 'auto',
      padding: '0.5rem'
    },
    playlistItem: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.75rem',
      borderRadius: '0.5rem',
      cursor: 'pointer',
      transition: 'background-color 0.2s'
    },
    playlistItemActive: {
      backgroundColor: '#dbeafe'
    },
    playlistItemThumbnail: {
      width: '40px',
      height: '40px',
      borderRadius: '0.375rem',
      objectFit: 'cover'
    },
    playlistItemText: {
      flex: 1,
      minWidth: 0
    },
    playlistItemTitle: {
      fontWeight: '500',
      fontSize: '0.875rem',
      ...lineClamp1
    },
    playlistItemSubtitle: {
      color: '#6b7280',
      fontSize: '0.75rem'
    },
    activeIndicator: {
      color: '#2563eb',
      fontSize: '0.75rem',
      fontWeight: 'bold'
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.wrapper}>
        {/* Header */}
        <div style={styles.header}>
          <h1 style={styles.title}>YouTube Downloader</h1>
          <p style={styles.subtitle}>Download your favorite music and videos</p>
        </div>

        {/* Tab Navigation */}
        <div style={styles.tabContainer}>
          <button
            onClick={() => {
              setActiveTab('download');
              setDownloadMode(null);
              setUrl('');
              setError('');
            }}
            style={{
              ...styles.tabButton,
              ...(activeTab === 'download' ? styles.tabButtonActive : styles.tabButtonInactive)
            }}
          >
            <Download style={{ display: 'inline', marginRight: '0.5rem' }} size={isMobile ? 18 : 20} />
            Download
          </button>
          <button
            onClick={() => setActiveTab('history')}
            style={{
              ...styles.tabButton,
              ...(activeTab === 'history' ? styles.tabButtonActive : styles.tabButtonInactive)
            }}
          >
            Library ({downloadHistory.length})
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div style={styles.errorAlert}>
            <XCircle size={isMobile ? 18 : 20} />
            {error}
          </div>
        )}

        {/* Download Tab */}
        {activeTab === 'download' && (
          <div style={styles.card}>
            {!downloadMode ? (
              <div style={styles.centerContent}>
                <h3 style={{ fontSize: isMobile ? '1.25rem' : '1.5rem', fontWeight: 'bold', color: '#1f2937', marginBottom: '1.5rem' }}>
                  What would you like to download?
                </h3>
                <div style={styles.modeSelection}>
                  <button
                    onClick={() => setDownloadMode('music')}
                    style={{
                      ...styles.modeButton,
                      background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                    }}
                  >
                    <Music size={isMobile ? 40 : 48} />
                    <span style={{ fontSize: isMobile ? '1.125rem' : '1.25rem', fontWeight: 'bold' }}>Music</span>
                    <span style={{ fontSize: '0.875rem', opacity: 0.9 }}>MP3 Audio</span>
                  </button>
                  <button
                    onClick={() => setDownloadMode('videos')}
                    style={{
                      ...styles.modeButton,
                      background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
                    }}
                  >
                    <Video size={isMobile ? 40 : 48} />
                    <span style={{ fontSize: isMobile ? '1.125rem' : '1.25rem', fontWeight: 'bold' }}>Videos</span>
                    <span style={{ fontSize: '0.875rem', opacity: 0.9 }}>MP4 Video</span>
                  </button>
                </div>
              </div>
            ) : (
              <div>
                {/* Mode Indicator */}
                <div style={styles.modeIndicator}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    {downloadMode === 'music' ? <Music size={isMobile ? 20 : 24} /> : <Video size={isMobile ? 20 : 24} />}
                    <span style={{ fontWeight: '600', fontSize: isMobile ? '0.875rem' : '1rem' }}>
                      Downloading as: {downloadMode === 'music' ? 'Music (MP3)' : 'Video (MP4)'}
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      setDownloadMode(null);
                      setUrl('');
                    }}
                    style={{
                      padding: isMobile ? '0.375rem 0.75rem' : '0.5rem 1rem',
                      backgroundColor: '#e5e7eb',
                      borderRadius: '0.5rem',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                      width: isMobile ? '100%' : 'auto',
                      marginTop: isMobile ? '0.5rem' : '0'
                    }}
                  >
                    Change
                  </button>
                </div>

                {/* URL Input */}
                <div style={{ marginBottom: '1.5rem' }}>
                  <h4 style={{ fontWeight: '600', marginBottom: '0.75rem', fontSize: isMobile ? '0.875rem' : '1rem' }}>
                    YouTube URL
                  </h4>
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder={isMobile ? "Paste YouTube link" : "Paste YouTube URL here"}
                    style={styles.input}
                  />
                </div>

                {/* Download Button */}
                <button
                  onClick={startDownload}
                  disabled={loading || !url}
                  style={{
                    ...styles.downloadButton,
                    ...(loading
                      ? { backgroundColor: '#9ca3af', cursor: 'not-allowed' }
                      : downloadMode === 'music'
                      ? { background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', color: 'white' }
                      : { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: 'white' })
                  }}
                >
                  {loading ? (
                    <>
                      <Loader style={{ animation: 'spin 1s linear infinite' }} size={isMobile ? 20 : 24} />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download size={isMobile ? 20 : 24} />
                      Download {downloadMode === 'music' ? 'Music' : 'Video'}
                    </>
                  )}
                </button>

                {/* Progress Display */}
                {(loading || downloadStatus) && (
                  <div style={styles.progressContainer}>
                    {currentDownload && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem', flexDirection: isMobile ? 'column' : 'row' }}>
                        {currentDownload.thumbnail && (
                          <img src={currentDownload.thumbnail} alt="" style={{ ...styles.videoThumbnail, width: isMobile ? '100%' : '8rem' }} />
                        )}
                        <div style={{ flex: 1, width: '100%' }}>
                          <p style={{ fontWeight: '600', fontSize: isMobile ? '0.75rem' : '0.875rem', ...lineClamp1 }}>
                            {currentDownload.title}
                          </p>
                          <p style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                            {downloadStatus === 'completed' ? 'Complete!' : downloadStatus === 'failed' ? 'Failed' : 'Downloading...'}
                          </p>
                        </div>
                      </div>
                    )}
                    <div style={styles.progressBar}>
                      <div
                        style={{
                          ...styles.progressFill,
                          width: `${progress}%`,
                          backgroundColor: downloadStatus === 'completed' 
                            ? '#10b981' 
                            : downloadStatus === 'failed' 
                            ? '#ef4444' 
                            : '#3b82f6'
                        }}
                      >
                        {progress}%
                      </div>
                    </div>
                    {downloadStatus === 'completed' && (
                      <div style={{ 
                        marginTop: '0.75rem', 
                        textAlign: 'center', 
                        color: '#059669', 
                        fontWeight: '600',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                        fontSize: isMobile ? '0.875rem' : '1rem'
                      }}>
                        <CheckCircle size={isMobile ? 18 : 20} />
                        Download Complete! Redirecting to library...
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div style={styles.card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: isMobile ? 'flex-start' : 'center', marginBottom: '1.5rem', flexDirection: isMobile ? 'column' : 'row', gap: isMobile ? '1rem' : '0' }}>
              <h3 style={{ fontSize: isMobile ? '1.25rem' : '1.5rem', fontWeight: 'bold' }}>My Library</h3>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', width: isMobile ? '100%' : 'auto' }}>
                <button
                  onClick={() => setHistoryFilter('all')}
                  style={{
                    ...styles.button,
                    ...(historyFilter === 'all' ? styles.buttonPrimary : { backgroundColor: '#e5e7eb' }),
                    padding: isMobile ? '0.5rem 0.875rem' : '0.75rem 1.5rem',
                    flex: isMobile ? '1' : 'none'
                  }}
                >
                  All
                </button>
                <button
                  onClick={() => setHistoryFilter('music')}
                  style={{
                    ...styles.button,
                    ...(historyFilter === 'music' ? styles.buttonPrimary : { backgroundColor: '#e5e7eb' }),
                    padding: isMobile ? '0.5rem 0.875rem' : '0.75rem 1.5rem',
                    flex: isMobile ? '1' : 'none'
                  }}
                >
                  <Music size={16} />
                  Music
                </button>
                <button
                  onClick={() => setHistoryFilter('videos')}
                  style={{
                    ...styles.button,
                    ...(historyFilter === 'videos' ? styles.buttonPrimary : { backgroundColor: '#e5e7eb' }),
                    padding: isMobile ? '0.5rem 0.875rem' : '0.75rem 1.5rem',
                    flex: isMobile ? '1' : 'none'
                  }}
                >
                  <Video size={16} />
                  Videos
                </button>
                <button
                  onClick={fetchDownloadHistory}
                  style={{
                    ...styles.button,
                    padding: isMobile ? '0.5rem 0.875rem' : '0.75rem 1.5rem',
                    backgroundColor: '#e5e7eb',
                    width: isMobile ? '100%' : 'auto'
                  }}
                >
                  Refresh
                </button>
              </div>
            </div>

            {/* Show filter status */}
            <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#f3f4f6', borderRadius: '0.5rem' }}>
              <span style={{ fontWeight: '600', color: '#374151', fontSize: isMobile ? '0.875rem' : '1rem' }}>
                Showing: 
                {historyFilter === 'all' && ' All Downloads'}
                {historyFilter === 'music' && ' Music (MP3)'}
                {historyFilter === 'videos' && ' Videos (MP4)'}
                {' '}({filteredHistory.length} items)
              </span>
            </div>

            {filteredHistory.length === 0 ? (
              <div style={{ textAlign: 'center', padding: isMobile ? '3rem 0' : '4rem 0', color: '#6b7280' }}>
                <Download size={isMobile ? 48 : 64} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                <p style={{ fontSize: isMobile ? '1rem' : '1.25rem' }}>
                  {downloadHistory.length === 0 ? 'No downloads yet' : `No ${historyFilter} downloads`}
                </p>
                <p style={{ fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                  {downloadHistory.length === 0 ? 'Start downloading your favorite content!' : `Try changing the filter or download some ${historyFilter}`}
                </p>
              </div>
            ) : (
              <div>
                {filteredHistory.map((download, index) => (
                  <div key={download.id} style={styles.historyItem}>
                    <img src={download.thumbnail} alt="" style={styles.historyThumbnail} />
                    <div style={{ flex: 1, width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
                        <h4 style={{ fontWeight: '600', ...lineClamp2, fontSize: isMobile ? '0.875rem' : '1rem', flex: 1 }}>{download.title}</h4>
                        <span style={{
                          padding: '0.25rem 0.5rem',
                          borderRadius: '0.25rem',
                          fontSize: '0.75rem',
                          fontWeight: 'bold',
                          backgroundColor: download.format === 'mp3' ? '#10b981' : '#f59e0b',
                          color: 'white'
                        }}>
                          {download.format.toUpperCase()}
                        </span>
                      </div>
                      <div style={{ fontSize: isMobile ? '0.75rem' : '0.875rem', color: '#6b7280' }}>
                        <p>Format: {download.format.toUpperCase()}</p>
                        <p>Size: {formatFileSize(download.file_size)}</p>
                        {download.duration > 0 && <p>Duration: {formatDuration(download.duration)}</p>}
                      </div>
                      <div style={styles.actionButtons}>
                        <button
                          onClick={() => playMedia(download, index)}
                          style={{ 
                            ...styles.button, 
                            ...styles.buttonPrimary,
                            flex: isMobile ? '1' : 'none',
                            justifyContent: 'center'
                          }}
                        >
                          <Play size={16} />
                          {!isMobile && 'Play'}
                        </button>
                        <button
                          onClick={() => window.open(`${API_BASE}/download-file/?path=${encodeURIComponent(download.file_path)}`, '_blank')}
                          style={{ 
                            ...styles.button, 
                            backgroundColor: '#059669', 
                            color: 'white',
                            flex: isMobile ? '1' : 'none',
                            justifyContent: 'center'
                          }}
                        >
                          <Download size={16} />
                          {!isMobile && 'Download'}
                        </button>
                        <button
                          onClick={() => deleteDownload(download.id, download.file_name)}
                          style={{ 
                            ...styles.button, 
                            backgroundColor: '#dc2626', 
                            color: 'white',
                            flex: isMobile ? '0' : 'none',
                            justifyContent: 'center',
                            padding: isMobile ? '0.625rem' : '0.75rem 1.5rem'
                          }}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div style={styles.footer}>
          <p>
            This app is created for educational/personal use only not business! created by{' '}
            <a 
              href="https://www.mfundodev.com" 
              target="_blank" 
              rel="noopener noreferrer"
              style={{ 
                color: '#2563eb', 
                textDecoration: 'underline',
                cursor: 'pointer'
              }}
            >
              mfundodev.com
            </a>
          </p>
        </div>
      </div>

      {/* Media Player */}
      {currentMedia && (
        <div style={styles.mediaPlayer}>
          <div style={styles.playerControls}>
            {/* Media Info */}
            <div style={styles.playerInfo}>
              <img src={currentMedia.thumbnail} alt="" style={styles.playerThumbnail} />
              <div style={styles.playerText}>
                <div style={styles.playerTitle}>{currentMedia.title}</div>
                <div style={styles.playerSubtitle}>
                  {currentMedia.format.toUpperCase()} • {formatFileSize(currentMedia.file_size)}
                </div>
              </div>
            </div>

            {/* Control Buttons */}
            <div style={styles.controlButtons}>
              <button
                onClick={toggleShuffle}
                style={{
                  ...styles.controlButton,
                  color: shuffleMode ? '#2563eb' : '#6b7280'
                }}
                title="Shuffle"
              >
                <Shuffle size={isMobile ? 16 : 18} />
              </button>
              
              <button
                onClick={playPrevious}
                style={styles.controlButton}
                title="Previous"
              >
                <SkipBack size={isMobile ? 16 : 18} />
              </button>
              
              <button
                onClick={togglePlayPause}
                style={{
                  ...styles.controlButton,
                  ...styles.playButton
                }}
                title={isPlaying ? "Pause" : "Play"}
              >
                {isPlaying ? (
                  <div style={{ width: isMobile ? '16px' : '18px', height: isMobile ? '16px' : '18px', backgroundColor: 'white' }} />
                ) : (
                  <Play size={isMobile ? 16 : 18} fill="white" />
                )}
              </button>
              
              <button
                onClick={playNext}
                style={styles.controlButton}
                title="Next"
              >
                <SkipForward size={isMobile ? 16 : 18} />
              </button>
              
              <button
                onClick={toggleRepeat}
                style={{
                  ...styles.controlButton,
                  color: repeatMode !== 'off' ? '#2563eb' : '#6b7280'
                }}
                title={`Repeat: ${repeatMode}`}
              >
                <Repeat size={isMobile ? 16 : 18} />
                {repeatMode === 'one' && (
                  <span style={{ 
                    position: 'absolute', 
                    fontSize: '8px', 
                    fontWeight: 'bold',
                    marginTop: '-8px'
                  }}>1</span>
                )}
              </button>
            </div>

            {/* Progress Bar */}
            <div style={styles.progressSection}>
              <span style={styles.timeDisplay}>{formatTime(currentTime)}</span>
              <input
                type="range"
                min="0"
                max={duration || 0}
                value={currentTime}
                onChange={handleSeek}
                style={styles.progressSlider}
              />
              <span style={styles.timeDisplay}>{formatTime(duration)}</span>
            </div>

            {/* Volume Control */}
            <div style={styles.volumeSection}>
              <button
                onClick={toggleMute}
                style={styles.controlButton}
                title={isMuted ? "Unmute" : "Mute"}
              >
                {isMuted || volume === 0 ? (
                  <VolumeX size={isMobile ? 16 : 18} />
                ) : (
                  <Volume2 size={isMobile ? 16 : 18} />
                )}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={volume}
                onChange={handleVolumeChange}
                style={styles.volumeSlider}
              />
            </div>

            {/* Playlist Button */}
            <button
              onClick={() => setShowPlaylist(true)}
              style={styles.controlButton}
              title="Playlist"
            >
              <List size={isMobile ? 16 : 18} />
            </button>
          </div>

          {/* Hidden Media Elements */}
          {currentMedia.format === 'mp3' ? (
            <audio
              ref={audioRef}
              src={`${API_BASE}/play-file/?path=${encodeURIComponent(currentMedia.file_path)}`}
              onTimeUpdate={handleTimeUpdate}
              onEnded={handleMediaEnd}
              onLoadedMetadata={handleTimeUpdate}
            />
          ) : (
            <video
              ref={videoRef}
              src={`${API_BASE}/play-file/?path=${encodeURIComponent(currentMedia.file_path)}`}
              onTimeUpdate={handleTimeUpdate}
              onEnded={handleMediaEnd}
              onLoadedMetadata={handleTimeUpdate}
              style={{ display: 'none' }}
            />
          )}
        </div>
      )}

      {/* Playlist Modal */}
      {showPlaylist && (
        <div style={styles.playlistOverlay} onClick={() => setShowPlaylist(false)}>
          <div style={styles.playlistModal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.playlistHeader}>
              <h3 style={styles.playlistTitle}>Playlist ({playlist.length} items)</h3>
              <button
                onClick={() => setShowPlaylist(false)}
                style={styles.playlistClose}
              >
                <X size={20} />
              </button>
            </div>
            <div style={styles.playlistContent}>
              {playlist.map((item, index) => (
                <div
                  key={item.id}
                  onClick={() => {
                    playMedia(item, index);
                    setShowPlaylist(false);
                  }}
                  style={{
                    ...styles.playlistItem,
                    ...(currentMedia && currentMedia.id === item.id ? styles.playlistItemActive : {})
                  }}
                >
                  <img src={item.thumbnail} alt="" style={styles.playlistItemThumbnail} />
                  <div style={styles.playlistItemText}>
                    <div style={styles.playlistItemTitle}>{item.title}</div>
                    <div style={styles.playlistItemSubtitle}>
                      {item.format.toUpperCase()} • {formatFileSize(item.file_size)}
                    </div>
                  </div>
                  {currentMedia && currentMedia.id === item.id && (
                    <div style={styles.activeIndicator}>▶</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <style>
        {`
          @keyframes spin {
            from {
              transform: rotate(0deg);
            }
            to {
              transform: rotate(360deg);
            }
          }
          
          input[type="range"] {
            -webkit-appearance: none;
            appearance: none;
            background: transparent;
            cursor: pointer;
          }
          
          input[type="range"]::-webkit-slider-track {
            background: #e5e7eb;
            height: 4px;
            border-radius: 2px;
          }
          
          input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            background: #2563eb;
            height: 16px;
            width: 16px;
            border-radius: 50%;
            cursor: pointer;
          }
          
          input[type="range"]::-moz-range-track {
            background: #e5e7eb;
            height: 4px;
            border-radius: 2px;
            border: none;
          }
          
          input[type="range"]::-moz-range-thumb {
            background: #2563eb;
            height: 16px;
            width: 16px;
            border-radius: 50%;
            cursor: pointer;
            border: none;
          }
        `}
      </style>
    </div>
  );
};

export default YouTubeDownloader;