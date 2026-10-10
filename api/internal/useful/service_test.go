package useful_test

import (
	"sync"
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
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

func TestToggleConcurrentSameUserNoDoubleCount(t *testing.T) {
	app := testutil.NewApp(t)
	user := testutil.MakeUser(t, app, "race@example.com")
	owner := authz.Owner{Kind: authz.KindUser, ID: user.Id}
	svc := useful.Service{App: app, Salt: "test-salt"}

	var wg sync.WaitGroup
	errs := make(chan error, 8)
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, err := svc.Toggle(owner, "race-1", true)
			if err != nil {
				errs <- err
			}
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		t.Fatal(err)
	}
	n, err := svc.Count("race-1")
	if err != nil {
		t.Fatal(err)
	}
	if n != 1 {
		t.Fatalf("concurrent toggles want count 1 got %d", n)
	}
}
