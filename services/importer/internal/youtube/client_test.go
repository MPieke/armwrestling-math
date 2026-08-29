package youtube

import (
	"errors"
	"strings"
	"testing"
)

func TestRedactProviderErrorRemovesAPIKey(t *testing.T) {
	secret := "api-key-value"
	err := redactProviderError(errors.New("request failed: key="+secret), secret)
	if strings.Contains(err, secret) {
		t.Fatalf("redacted error contains API key: %q", err)
	}
	if !strings.Contains(err, "[REDACTED]") {
		t.Fatalf("redacted error = %q, want redaction marker", err)
	}
}
