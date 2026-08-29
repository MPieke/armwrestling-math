package config

import "testing"

func TestLoadRequiresProviderAndDatabaseSettings(t *testing.T) {
	settings := map[string]string{
		"DATABASE_URL":    "postgres://db/app",
		"YOUTUBE_API_KEY": "youtube-key",
		"GEMINI_API_KEY":  "gemini-key",
		"GEMINI_MODEL":    "gemini-2.5-flash",
	}

	configuration, err := Load(func(name string) string { return settings[name] })
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if configuration.DatabaseURL != settings["DATABASE_URL"] {
		t.Fatalf("DatabaseURL = %q, want %q", configuration.DatabaseURL, settings["DATABASE_URL"])
	}
	if configuration.GeminiModel != settings["GEMINI_MODEL"] {
		t.Fatalf("GeminiModel = %q, want %q", configuration.GeminiModel, settings["GEMINI_MODEL"])
	}
}

func TestLoadAppliesProviderBaseURLDefaults(t *testing.T) {
	settings := map[string]string{
		"DATABASE_URL":    "postgres://db/app",
		"YOUTUBE_API_KEY": "youtube-key",
		"GEMINI_API_KEY":  "gemini-key",
		"GEMINI_MODEL":    "gemini-2.5-flash",
	}

	configuration, err := Load(func(name string) string { return settings[name] })
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if configuration.YouTubeAPIBaseURL != defaultYouTubeAPIBaseURL {
		t.Fatalf("YouTubeAPIBaseURL = %q, want %q", configuration.YouTubeAPIBaseURL, defaultYouTubeAPIBaseURL)
	}
	if configuration.GeminiAPIBaseURL != defaultGeminiAPIBaseURL {
		t.Fatalf("GeminiAPIBaseURL = %q, want %q", configuration.GeminiAPIBaseURL, defaultGeminiAPIBaseURL)
	}
}

func TestLoadUsesExplicitProviderBaseURLs(t *testing.T) {
	settings := map[string]string{
		"DATABASE_URL":         "postgres://db/app",
		"YOUTUBE_API_KEY":      "youtube-key",
		"GEMINI_API_KEY":       "gemini-key",
		"GEMINI_MODEL":         "gemini-2.5-flash",
		"YOUTUBE_API_BASE_URL": "http://youtube.test",
		"GEMINI_API_BASE_URL":  "http://gemini.test",
	}

	configuration, err := Load(func(name string) string { return settings[name] })
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if configuration.YouTubeAPIBaseURL != settings["YOUTUBE_API_BASE_URL"] {
		t.Fatalf("YouTubeAPIBaseURL = %q, want %q", configuration.YouTubeAPIBaseURL, settings["YOUTUBE_API_BASE_URL"])
	}
	if configuration.GeminiAPIBaseURL != settings["GEMINI_API_BASE_URL"] {
		t.Fatalf("GeminiAPIBaseURL = %q, want %q", configuration.GeminiAPIBaseURL, settings["GEMINI_API_BASE_URL"])
	}
}

func TestLoadReportsAllMissingRequiredSettings(t *testing.T) {
	_, err := Load(func(string) string { return "" })
	if err == nil {
		t.Fatal("Load returned nil error for missing required settings")
	}
	for _, name := range []string{"DATABASE_URL", "YOUTUBE_API_KEY", "GEMINI_API_KEY", "GEMINI_MODEL"} {
		if !contains(err.Error(), name) {
			t.Errorf("error %q does not mention missing %s", err, name)
		}
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
