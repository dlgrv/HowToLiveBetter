package useful_test

import (
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
	"github.com/dlgrv/HowToLiveBetter/api/internal/useful"
)

func TestToggleIdempotent(t *testing.T) {
	app := testutil.NewApp(t)
	_, owner := testutil.MakeGuest(t, app)
	svc := useful.Service{App: app, Salt: "test-salt"}
	r1, err := svc.Toggle(owner, "entry-1", true)
	if err != nil {
		t.Fatal(err)
	}
	if !r1.Useful || r1.Count != 1 {
		t.Fatalf("%+v", r1)
	}
	r2, err := svc.Toggle(owner, "entry-1", true)
	if err != nil {
		t.Fatal(err)
	}
	if r2.Count != 1 {
		t.Fatalf("idempotent count want 1 got %d", r2.Count)
	}
	r3, err := svc.Toggle(owner, "entry-1", false)
	if err != nil {
		t.Fatal(err)
	}
	if r3.Useful || r3.Count != 0 {
		t.Fatalf("%+v", r3)
	}
}
