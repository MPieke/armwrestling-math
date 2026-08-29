package youtube

import (
	"encoding/json"
	"time"
)

type Video struct {
	ID              string
	Title           string
	ChannelName     string
	PublishedAt     time.Time
	DurationSeconds int
	URL             string
	RawPayload      json.RawMessage
}
