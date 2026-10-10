package devauth_test

import (
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/devauth"
	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
	"github.com/dlgrv/HowToLiveBetter/api/internal/useful"
)

func TestIssueTokenIdempotent(t *testing.T) {
	app := testutil.NewApp(t)
	tok1, err := devauth.IssueToken(app)
	if err != nil || tok1 == "" {
		t.Fatalf("tok1=%q err=%v", tok1, err)
	}
	tok2, err := devauth.IssueToken(app)
	if err != nil || tok2 == "" {
		t.Fatalf("tok2=%q err=%v", tok2, err)
	}
	user, err := app.FindAuthRecordByEmail("users", devauth.StubEmail)
	if err != nil {
		t.Fatal(err)
	}
	owner := authz.Owner{Kind: authz.KindUser, ID: user.Id}
	res, err := useful.Service{App: app, Salt: "t"}.Toggle(owner, "e-dev", true)
	if err != nil || !res.Useful || res.Count != 1 {
		t.Fatalf("%+v err=%v", res, err)
	}
}
