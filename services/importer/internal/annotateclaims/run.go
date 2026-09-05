// Package annotateclaims is the composition root for cmd/annotate-claims:
// list claims this (model, prompt_version) hasn't annotated yet, call the
// annotator, validate, persist. One claim's failure doesn't stop the batch,
// mirroring internal/youtubeingest's per-candidate error handling.
package annotateclaims

import (
	"context"
	"encoding/json"
	"log/slog"

	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/annotate"
	"github.com/mpieke/armwrestling-math/services/importer/internal/dbgen"
)

type Options struct {
	PromptVersion string
	Logger        *slog.Logger
}

type Result struct {
	Selected  int
	Completed int
	Failed    int
}

func Run(ctx context.Context, pool *pgxpool.Pool, annotator annotate.Annotator, options Options) (Result, error) {
	logger := options.Logger
	if logger == nil {
		logger = slog.Default()
	}
	queries := dbgen.New(pool)
	claims, err := queries.ListClaimsMissingAnnotation(ctx, dbgen.ListClaimsMissingAnnotationParams{
		Model:         annotator.ModelName(),
		PromptVersion: options.PromptVersion,
	})
	if err != nil {
		return Result{}, err
	}
	result := Result{Selected: len(claims)}
	logger.Info("annotation started", "model", annotator.ModelName(), "prompt_version", options.PromptVersion, "claims", len(claims))
	for _, claim := range claims {
		if err := annotateOne(ctx, queries, annotator, options.PromptVersion, claim, logger); err != nil {
			result.Failed++
			continue
		}
		result.Completed++
	}
	logger.Info("annotation completed", "selected", result.Selected, "completed", result.Completed, "failed", result.Failed)
	return result, nil
}

func annotateOne(ctx context.Context, queries *dbgen.Queries, annotator annotate.Annotator, promptVersion string, claim dbgen.ListClaimsMissingAnnotationRow, logger *slog.Logger) error {
	competitors, err := queries.ListMatchCompetitors(ctx, claim.MatchID)
	if err != nil {
		return err
	}
	names := make([]string, 0, len(competitors))
	idByName := make(map[string]int64, len(competitors))
	for _, competitor := range competitors {
		names = append(names, competitor.CanonicalName)
		idByName[competitor.CanonicalName] = competitor.ID
	}

	annotation, _, _, err := annotator.Annotate(ctx, annotate.ClaimContext{
		ClaimID: claim.ID, ClaimText: claim.ClaimText, Competitors: names,
	})
	if err != nil {
		logger.Error("annotation request failed", "claim_id", claim.ID, "error", err)
		return err
	}
	if err := annotate.ValidateAnnotation(annotation); err != nil {
		logger.Error("annotation validation failed", "claim_id", claim.ID, "error", err)
		return err
	}

	payload, err := json.Marshal(annotation)
	if err != nil {
		return err
	}
	_, err = queries.UpsertClaimAnnotation(ctx, dbgen.UpsertClaimAnnotationParams{
		ClaimID:          claim.ID,
		Model:            annotator.ModelName(),
		PromptVersion:    promptVersion,
		ClaimType:        annotation.ClaimType,
		Concepts:         annotation.Concepts,
		SubjectAthleteID: resolveSubjectID(annotation.SubjectAthleteName, idByName),
		Arm:              resolveArm(annotation.Arm),
		Temporality:      annotation.Temporality,
		Certainty:        annotation.Certainty,
		RawPayload:       payload,
	})
	if err != nil {
		logger.Error("annotation persistence failed", "claim_id", claim.ID, "error", err)
	}
	return err
}

// resolveSubjectID maps the model's free-text athlete name back to an id
// without ever asking the model to output a foreign key. A name that
// doesn't exactly match either competitor (including the deliberate empty
// string for "general/both") resolves to no subject, not an error.
func resolveSubjectID(name string, idByName map[string]int64) pgtype.Int8 {
	if id, ok := idByName[name]; ok {
		return pgtype.Int8{Int64: id, Valid: true}
	}
	return pgtype.Int8{}
}

// resolveArm maps the schema's three-value "left|right|unclear" onto the
// nullable two-value database column -- "unclear" and anything else become
// NULL rather than a fourth check-constraint value.
func resolveArm(arm string) pgtype.Text {
	if arm == "left" || arm == "right" {
		return pgtype.Text{String: arm, Valid: true}
	}
	return pgtype.Text{}
}
