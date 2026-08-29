package config

import (
	"log/slog"
	"testing"
	"time"
)

func TestLoadRequiresProviderAndDatabaseSettings(t *testing.T) {
	settings := map[string]string{
		"DATABASE_URL":            "postgres://db/app",
		"YOUTUBE_API_KEY":         "youtube-key",
		"OPENAI_API_KEY":          "openai-key",
		"OPENAI_EXTRACTION_MODEL": "gpt-4.1-mini",
	}

	configuration, err := Load(func(name string) string { return settings[name] })
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if configuration.DatabaseURL != settings["DATABASE_URL"] {
		t.Fatalf("DatabaseURL = %q, want %q", configuration.DatabaseURL, settings["DATABASE_URL"])
	}
	if configuration.HTTPTimeout != defaultHTTPTimeout {
		t.Fatalf("HTTPTimeout = %s, want %s", configuration.HTTPTimeout, defaultHTTPTimeout)
	}
	if configuration.AudioTimeout != defaultAudioTimeout {
		t.Fatalf("AudioTimeout = %s, want %s", configuration.AudioTimeout, defaultAudioTimeout)
	}
	if configuration.LogFormat != "text" || configuration.LogLevel != slog.LevelInfo {
		t.Fatalf("logging defaults = (%q, %s), want (text, INFO)", configuration.LogFormat, slog.LevelInfo)
	}
}

func TestLoadAppliesProviderBaseURLDefaults(t *testing.T) {
	settings := map[string]string{
		"DATABASE_URL":            "postgres://db/app",
		"YOUTUBE_API_KEY":         "youtube-key",
		"OPENAI_API_KEY":          "openai-key",
		"OPENAI_EXTRACTION_MODEL": "gpt-4.1-mini",
	}

	configuration, err := Load(func(name string) string { return settings[name] })
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if configuration.YouTubeAPIBaseURL != defaultYouTubeAPIBaseURL {
		t.Fatalf("YouTubeAPIBaseURL = %q, want %q", configuration.YouTubeAPIBaseURL, defaultYouTubeAPIBaseURL)
	}
}

func TestLoadUsesExplicitProviderBaseURLs(t *testing.T) {
	settings := map[string]string{
		"DATABASE_URL":            "postgres://db/app",
		"YOUTUBE_API_KEY":         "youtube-key",
		"OPENAI_API_KEY":          "openai-key",
		"OPENAI_EXTRACTION_MODEL": "gpt-4.1-mini",
		"YOUTUBE_API_BASE_URL":    "http://youtube.test",
		"OPENAI_API_BASE_URL":     "http://openai.test",
	}

	configuration, err := Load(func(name string) string { return settings[name] })
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if configuration.YouTubeAPIBaseURL != settings["YOUTUBE_API_BASE_URL"] {
		t.Fatalf("YouTubeAPIBaseURL = %q, want %q", configuration.YouTubeAPIBaseURL, settings["YOUTUBE_API_BASE_URL"])
	}
	if configuration.OpenAIAPIBaseURL != settings["OPENAI_API_BASE_URL"] {
		t.Fatalf("OpenAIAPIBaseURL = %q, want %q", configuration.OpenAIAPIBaseURL, settings["OPENAI_API_BASE_URL"])
	}
}

func TestLoadReportsAllMissingRequiredSettings(t *testing.T) {
	_, err := Load(func(string) string { return "" })
	if err == nil {
		t.Fatal("Load returned nil error for missing required settings")
	}
	for _, name := range []string{"DATABASE_URL", "YOUTUBE_API_KEY", "OPENAI_API_KEY", "OPENAI_EXTRACTION_MODEL"} {
		if !contains(err.Error(), name) {
			t.Errorf("error %q does not mention missing %s", err, name)
		}
	}
}

func TestLoadParsesLoggingAndTimeoutSettings(t *testing.T) {
	settings := map[string]string{
		"DATABASE_URL":            "postgres://db/app",
		"YOUTUBE_API_KEY":         "youtube-key",
		"OPENAI_API_KEY":          "openai-key",
		"OPENAI_EXTRACTION_MODEL": "gpt-4.1-mini",
		"INGEST_HTTP_TIMEOUT":     "17s",
		"INGEST_AUDIO_TIMEOUT":    "23m",
		"INGEST_LOG_FORMAT":       "json",
		"INGEST_LOG_LEVEL":        "debug",
	}

	configuration, err := Load(func(name string) string { return settings[name] })
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if configuration.HTTPTimeout != 17*time.Second {
		t.Fatalf("HTTPTimeout = %s, want 17s", configuration.HTTPTimeout)
	}
	if configuration.AudioTimeout != 23*time.Minute {
		t.Fatalf("AudioTimeout = %s, want 23m", configuration.AudioTimeout)
	}
	if configuration.LogFormat != "json" || configuration.LogLevel != slog.LevelDebug {
		t.Fatalf("logging settings = (%q, %s), want (json, DEBUG)", configuration.LogFormat, slog.LevelDebug)
	}
}

func TestLoadRejectsInvalidOperationalSettings(t *testing.T) {
	base := map[string]string{
		"DATABASE_URL":            "postgres://db/app",
		"YOUTUBE_API_KEY":         "youtube-key",
		"OPENAI_API_KEY":          "openai-key",
		"OPENAI_EXTRACTION_MODEL": "gpt-4.1-mini",
	}
	for name, value := range map[string]string{
		"INGEST_HTTP_TIMEOUT":  "not-a-duration",
		"INGEST_AUDIO_TIMEOUT": "not-a-duration",
		"INGEST_LOG_FORMAT":    "xml",
		"INGEST_LOG_LEVEL":     "verbose",
	} {
		t.Run(name, func(t *testing.T) {
			settings := make(map[string]string, len(base)+1)
			for key, setting := range base {
				settings[key] = setting
			}
			settings[name] = value
			if _, err := Load(func(key string) string { return settings[key] }); err == nil {
				t.Fatalf("Load accepted invalid %s", name)
			}
		})
	}
}

func contains(value, substring string) bool {
	for i := 0; i+len(substring) <= len(value); i++ {
		if value[i:i+len(substring)] == substring {
			return true
		}
	}
	return false
}
