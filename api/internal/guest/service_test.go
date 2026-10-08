package guest_test

import (
	"errors"
	"testing"
	"time"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/guest"
	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
	"github.com/pocketbase/dbx"
)

func TestCreateAndClaim(t *testing.T) {
	app := testutil.NewApp(t)
	svc := guest.Service{App: app, GuestTTL: 24 * time.Hour, ClaimTTL: 10 * time.Minute}
	token, _, err := svc.CreateSession()
	if err != nil {
		t.Fatal(err)
	}
	if len(token) < 20 {
		t.Fatalf("token too short: %q", token)
	}
	rec, err := app.FindFirstRecordByFilter("guest_sessions", "tokenHash = {:h}", dbx.Params{"h": authz.HashToken(token)})
	if err != nil {
		t.Fatal(err)
	}
	if rec.GetString("tokenHash") != authz.HashToken(token) {
		t.Fatal("hash mismatch")
	}
	code, _, err := svc.CreateClaimCode(rec.Id)
	if err != nil {
		t.Fatal(err)
	}
	newTok, _, err := svc.Claim(code)
	if err != nil {
		t.Fatal(err)
	}
	if newTok == token {
		t.Fatal("expected rotated token")
	}
	_, _, err = svc.Claim(code)
	if !errors.Is(err, guest.ErrClaimUsed) {
		t.Fatalf("want used, got %v", err)
	}
}
