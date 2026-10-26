package selfcheck_test

import (
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/selfcheck"
	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
)

func TestPutGetRoundtrip(t *testing.T) {
	app := testutil.NewApp(t)
	_, owner := testutil.MakeGuest(t, app)
	svc := selfcheck.Service{App: app}

	want := selfcheck.Answers{"1-1": 1, "2-3": 0}
	if err := svc.Put(owner, want); err != nil {
		t.Fatal(err)
	}
	got, err := svc.Get(owner)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 2 || got["1-1"] != 1 || got["2-3"] != 0 {
		t.Fatalf("got %+v", got)
	}
}

func TestGetEmpty(t *testing.T) {
	app := testutil.NewApp(t)
	_, owner := testutil.MakeGuest(t, app)
	got, err := selfcheck.Service{App: app}.Get(owner)
	if err != nil || got == nil || len(got) != 0 {
		t.Fatalf("want empty map, got %+v err=%v", got, err)
	}
}

func TestPutReplacesWholeMap(t *testing.T) {
	app := testutil.NewApp(t)
	_, owner := testutil.MakeGuest(t, app)
	svc := selfcheck.Service{App: app}
	_ = svc.Put(owner, selfcheck.Answers{"1-1": 1, "1-2": 0})
	if err := svc.Put(owner, selfcheck.Answers{"3-1": 1}); err != nil {
		t.Fatal(err)
	}
	got, _ := svc.Get(owner)
	if len(got) != 1 || got["3-1"] != 1 {
		t.Fatalf("put must replace the whole map, got %+v", got)
	}
}

func TestPutValidation(t *testing.T) {
	app := testutil.NewApp(t)
	_, owner := testutil.MakeGuest(t, app)
	svc := selfcheck.Service{App: app}

	cases := []selfcheck.Answers{
		{},
		{"": 1},
		{"1-1": 2},
		{"1-1": -1},
	}
	for i, answers := range cases {
		if err := svc.Put(owner, answers); err == nil {
			t.Fatalf("case %d: expected error", i)
		}
	}
}

func TestGuestAndUserIsolated(t *testing.T) {
	app := testutil.NewApp(t)
	_, gOwner := testutil.MakeGuest(t, app)
	user := testutil.MakeUser(t, app, "sc@example.com")
	uOwner := authz.Owner{Kind: authz.KindUser, ID: user.Id}
	svc := selfcheck.Service{App: app}

	_ = svc.Put(gOwner, selfcheck.Answers{"1-1": 1})
	got, _ := svc.Get(uOwner)
	if len(got) != 0 {
		t.Fatalf("user must not see guest answers, got %+v", got)
	}
}

func TestOverlaySrcWins(t *testing.T) {
	dst := selfcheck.Answers{"1-1": 0, "1-2": 1}
	src := selfcheck.Answers{"1-1": 1, "2-1": 0}
	got := selfcheck.Overlay(dst, src)
	if len(got) != 3 || got["1-1"] != 1 || got["1-2"] != 1 || got["2-1"] != 0 {
		t.Fatalf("got %+v", got)
	}
}
