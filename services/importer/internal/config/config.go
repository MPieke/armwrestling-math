package config

import (
	"fmt"
	"strings"
)

const (
	defaultYouTubeAPIBaseURL = "https://www.googleapis.com"
	defaultGeminiAPIBaseURL  = "https://generativelanguage.googleapis.com"
)

// Config contains only values needed to construct the YouTube ingestion
// runtime. Environment loading is deliberately owned by the caller so CI and
// deployed processes can use their native secret injection mechanisms.
type Config struct {
	DatabaseURL       string
	YouTubeAPIKey     string
	GeminiAPIKey      string
	GeminiModel       string
	YouTubeAPIBaseURL string
	GeminiAPIBaseURL  string
}

// Load reads configuration from getenv and applies defaults for optional
// provider endpoints. It never reads files or mutates the process environment.
func Load(getenv func(string) string) (Config, error) {
	required := []string{"DATABASE_URL", "YOUTUBE_API_KEY", "GEMINI_API_KEY", "GEMINI_MODEL"}
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
		DatabaseURL:       getenv("DATABASE_URL"),
		YouTubeAPIKey:     getenv("YOUTUBE_API_KEY"),
		GeminiAPIKey:      getenv("GEMINI_API_KEY"),
		GeminiModel:       getenv("GEMINI_MODEL"),
		YouTubeAPIBaseURL: getenv("YOUTUBE_API_BASE_URL"),
		GeminiAPIBaseURL:  getenv("GEMINI_API_BASE_URL"),
	}
	if configuration.YouTubeAPIBaseURL == "" {
		configuration.YouTubeAPIBaseURL = defaultYouTubeAPIBaseURL
	}
	if configuration.GeminiAPIBaseURL == "" {
		configuration.GeminiAPIBaseURL = defaultGeminiAPIBaseURL
	}
	return configuration, nil
}
