package youtube

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/mpieke/armwrestling-math/services/importer/internal/research"
)

type Client struct {
	HTTPClient *http.Client
	BaseURL    string
	APIKey     string
}

func (client Client) Search(ctx context.Context, query string, maximum int) ([]research.Candidate, error) {
	values := url.Values{"part": {"snippet"}, "type": {"video"}, "order": {"relevance"}, "maxResults": {strconv.Itoa(maximum)}, "q": {query}, "key": {client.APIKey}}
	var response struct {
		Items []struct {
			ID struct {
				VideoID string `json:"videoId"`
			} `json:"id"`
		} `json:"items"`
	}
	raw, err := client.get(ctx, "/youtube/v3/search?"+values.Encode())
	if err != nil {
		return nil, err
	}
	if err := json.Unmarshal(raw, &response); err != nil {
		return nil, fmt.Errorf("decode YouTube search response: %w", err)
	}
	candidates := make([]research.Candidate, 0, len(response.Items))
	for _, item := range response.Items {
		if item.ID.VideoID == "" {
			return nil, fmt.Errorf("YouTube search returned an item without video ID")
		}
		candidates = append(candidates, research.Candidate{VideoID: item.ID.VideoID, MatchedQueries: []string{query}})
	}
	return candidates, nil
}

func (client Client) Video(ctx context.Context, videoID string) (Video, error) {
	values := url.Values{"part": {"snippet,contentDetails"}, "id": {videoID}, "key": {client.APIKey}}
	var response struct {
		Items []struct {
			ID      string `json:"id"`
			Snippet struct {
				Title        string `json:"title"`
				ChannelTitle string `json:"channelTitle"`
				PublishedAt  string `json:"publishedAt"`
			} `json:"snippet"`
			ContentDetails struct {
				Duration string `json:"duration"`
			} `json:"contentDetails"`
		} `json:"items"`
	}
	raw, err := client.get(ctx, "/youtube/v3/videos?"+values.Encode())
	if err != nil {
		return Video{}, err
	}
	if err := json.Unmarshal(raw, &response); err != nil {
		return Video{}, fmt.Errorf("decode YouTube video response: %w", err)
	}
	if len(response.Items) != 1 || response.Items[0].ID != videoID {
		return Video{}, fmt.Errorf("YouTube video %q is missing", videoID)
	}
	item := response.Items[0]
	publishedAt, err := time.Parse(time.RFC3339, item.Snippet.PublishedAt)
	if err != nil {
		return Video{}, fmt.Errorf("parse YouTube publication time: %w", err)
	}
	duration, err := parseDuration(item.ContentDetails.Duration)
	if err != nil {
		return Video{}, err
	}
	return Video{ID: videoID, Title: item.Snippet.Title, ChannelName: item.Snippet.ChannelTitle, PublishedAt: publishedAt, DurationSeconds: duration, URL: "https://www.youtube.com/watch?v=" + videoID, RawPayload: raw}, nil
}

func (client Client) get(ctx context.Context, path string) (json.RawMessage, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, strings.TrimRight(client.BaseURL, "/")+path, nil)
	if err != nil {
		return nil, err
	}
	response, err := client.HTTPClient.Do(request)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()
	raw, err := io.ReadAll(response.Body)
	if err != nil {
		return nil, err
	}
	if response.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("YouTube HTTP %d: %s", response.StatusCode, raw)
	}
	return raw, nil
}

func parseDuration(value string) (int, error) {
	var hours, minutes, seconds int
	if _, err := fmt.Sscanf(value, "PT%dH%dM%dS", &hours, &minutes, &seconds); err == nil {
		return hours*3600 + minutes*60 + seconds, nil
	}
	if _, err := fmt.Sscanf(value, "PT%dM%dS", &minutes, &seconds); err == nil {
		return minutes*60 + seconds, nil
	}
	if _, err := fmt.Sscanf(value, "PT%dM", &minutes); err == nil {
		return minutes * 60, nil
	}
	if _, err := fmt.Sscanf(value, "PT%dS", &seconds); err == nil {
		return seconds, nil
	}
	return 0, fmt.Errorf("unsupported YouTube duration %q", value)
}
