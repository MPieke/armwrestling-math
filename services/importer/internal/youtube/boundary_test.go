package youtube

import (
	"os/exec"
	"strings"
	"testing"
)

func TestPackageHasNoDatabaseDependencies(t *testing.T) {
	output, err := exec.Command("go", "list", "-f", `{{join .Imports "\n"}}`, ".").CombinedOutput()
	if err != nil {
		t.Fatalf("go list: %v\n%s", err, output)
	}
	dependencies := string(output)
	for _, forbidden := range []string{"/internal/dbgen", "github.com/jackc/pgx"} {
		if strings.Contains(dependencies, forbidden) {
			t.Fatalf("youtube package depends on forbidden database package %q", forbidden)
		}
	}
}
