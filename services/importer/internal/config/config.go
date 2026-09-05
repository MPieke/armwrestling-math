package config

import (
	"fmt"
	"log/slog"
	"strings"
	"time"
)

const (
	defaultYouTubeAPIBaseURL     = "https://www.googleapis.com"
	defaultOpenAIAPIBaseURL      = "https://api.openai.com"
	defaultWhisperServerBaseURL  = "http://127.0.0.1:8080"
	defaultHTTPTimeout           = 60 * time.Second
	defaultAudioTimeout          = 15 * time.Minute
	TranscriptionProviderOpenAI  = "openai"
	TranscriptionProviderWhisper = "whisper_cpp"
)

// Config contains only values needed to construct the YouTube ingestion
// runtime. Environment loading is deliberately owned by the caller so CI and
// deployed processes can use their native secret injection mechanisms.
type Config struct {
	DatabaseURL              string
	YouTubeAPIKey            string
	YouTubeAPIBaseURL        string
	OpenAIAPIKey             string
	OpenAIAPIBaseURL         string
	OpenAITranscriptionModel string
	OpenAIExtractionModel    string
	TranscriptionProvider    string
	WhisperServerBaseURL     string
	HTTPTimeout              time.Duration
	AudioTimeout             time.Duration
	LogFormat                string
	LogLevel                 slog.Level
}

// Load reads configuration from getenv and applies defaults for optional
// provider endpoints. It never reads files or mutates the process environment.
func Load(getenv func(string) string) (Config, error) {
	required := []string{"DATABASE_URL", "YOUTUBE_API_KEY", "OPENAI_API_KEY", "OPENAI_EXTRACTION_MODEL"}
	missing := make([]string, 0, len(required))
	for _, name := range required {
		if strings.TrimSpace(getenv(name)) == "" {
			missing = append(missing, name)
		}
	}
	if len(missing) > 0 {
		return Config{}, fmt.Errorf("missing required environment variables: %s", strings.Join(missing, ", "))
	}

	configuration := Config{
		DatabaseURL:              getenv("DATABASE_URL"),
		YouTubeAPIKey:            getenv("YOUTUBE_API_KEY"),
		YouTubeAPIBaseURL:        getenv("YOUTUBE_API_BASE_URL"),
		OpenAIAPIKey:             getenv("OPENAI_API_KEY"),
		OpenAIAPIBaseURL:         getenv("OPENAI_API_BASE_URL"),
		OpenAITranscriptionModel: getenv("OPENAI_TRANSCRIPTION_MODEL"),
		OpenAIExtractionModel:    getenv("OPENAI_EXTRACTION_MODEL"),
	}
	if configuration.YouTubeAPIBaseURL == "" {
		configuration.YouTubeAPIBaseURL = defaultYouTubeAPIBaseURL
	}
	if configuration.OpenAIAPIBaseURL == "" {
		configuration.OpenAIAPIBaseURL = defaultOpenAIAPIBaseURL
	}
	if configuration.OpenAITranscriptionModel == "" {
		configuration.OpenAITranscriptionModel = "whisper-1"
	}
	configuration.TranscriptionProvider = getenv("TRANSCRIPTION_PROVIDER")
	if configuration.TranscriptionProvider == "" {
		configuration.TranscriptionProvider = TranscriptionProviderOpenAI
	}
	if configuration.TranscriptionProvider != TranscriptionProviderOpenAI && configuration.TranscriptionProvider != TranscriptionProviderWhisper {
		return Config{}, fmt.Errorf("TRANSCRIPTION_PROVIDER must be %q or %q, got %q", TranscriptionProviderOpenAI, TranscriptionProviderWhisper, configuration.TranscriptionProvider)
	}
	configuration.WhisperServerBaseURL = getenv("WHISPER_SERVER_BASE_URL")
	if configuration.WhisperServerBaseURL == "" {
		configuration.WhisperServerBaseURL = defaultWhisperServerBaseURL
	}
	configuration.HTTPTimeout = defaultHTTPTimeout
	if value := getenv("INGEST_HTTP_TIMEOUT"); value != "" {
		parsed, err := time.ParseDuration(value)
		if err != nil || parsed <= 0 {
			return Config{}, fmt.Errorf("INGEST_HTTP_TIMEOUT must be a positive duration, got %q", value)
		}
		configuration.HTTPTimeout = parsed
	}
	configuration.AudioTimeout = defaultAudioTimeout
	if value := getenv("INGEST_AUDIO_TIMEOUT"); value != "" {
		parsed, err := time.ParseDuration(value)
		if err != nil || parsed <= 0 {
			return Config{}, fmt.Errorf("INGEST_AUDIO_TIMEOUT must be a positive duration, got %q", value)
		}
		configuration.AudioTimeout = parsed
	}
	configuration.LogFormat = getenv("INGEST_LOG_FORMAT")
	if configuration.LogFormat == "" {
		configuration.LogFormat = "text"
	}
	if configuration.LogFormat != "text" && configuration.LogFormat != "json" {
		return Config{}, fmt.Errorf("INGEST_LOG_FORMAT must be text or json, got %q", configuration.LogFormat)
	}
	configuration.LogLevel = slog.LevelInfo
	if value := strings.ToLower(getenv("INGEST_LOG_LEVEL")); value != "" {
		switch value {
		case "debug":
			configuration.LogLevel = slog.LevelDebug
		case "info":
			configuration.LogLevel = slog.LevelInfo
		case "warn", "warning":
			configuration.LogLevel = slog.LevelWarn
		case "error":
			configuration.LogLevel = slog.LevelError
		default:
			return Config{}, fmt.Errorf("INGEST_LOG_LEVEL must be debug, info, warn, or error, got %q", value)
		}
	}
	return configuration, nil
}
