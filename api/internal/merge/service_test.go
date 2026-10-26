package merge_test

import (
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/library"
	"github.com/dlgrv/HowToLiveBetter/api/internal/merge"
	"github.com/dlgrv/HowToLiveBetter/api/internal/selfcheck"
	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
	"github.com/dlgrv/HowToLiveBetter/api/internal/useful"
)

func TestMergeGuestIntoUser(t *testing.T) {
	app := testutil.NewApp(t)
	_, gOwner := testutil.MakeGuest(t, app)
	user := testutil.MakeUser(t, app, "merge@example.com")
	lib := library.Service{App: app}
	_ = lib.UpsertBookmark(gOwner, "bm1", "")
	_ = lib.PutReading(gOwner, "03", 0.2)
	sc := selfcheck.Service{App: app}
	_ = sc.Put(gOwner, selfcheck.Answers{"1-1": 1})
	uSvc := useful.Service{App: app, Salt: "s"}
	_, _ = uSvc.Toggle(gOwner, "e1", true)

	svc := merge.Service{App: app, Library: lib, VoteSalt: "s"}
	res, err := svc.MergeGuestIntoUser(gOwner.ID, user.Id)
	if err != nil {
		t.Fatal(err)
	}
	if res.BookmarksMerged != 1 || !res.ReadingMerged || res.SelfcheckMerged != 1 {
		t.Fatalf("%+v", res)
	}
	uOwner := authz.Owner{Kind: authz.KindUser, ID: user.Id}
	items, _ := lib.ListBookmarks(uOwner)
	if len(items) != 1 {
		t.Fatalf("bookmarks %+v", items)
	}
	scGot, _ := sc.Get(uOwner)
	if scGot["1-1"] != 1 {
		t.Fatalf("selfcheck answers not merged: %+v", scGot)
	}
	got, err := uSvc.Get(uOwner, "e1")
	if err != nil || !got.Useful || got.Count != 1 {
		t.Fatalf("useful vote not visible to user after merge: %+v err=%v", got, err)
	}
	rec, err := app.FindRecordById("guest_sessions", gOwner.ID)
	if err != nil || rec.GetString("status") != "merged" {
		t.Fatalf("status %v %v", err, rec)
	}
	_, err = svc.MergeGuestIntoUser(gOwner.ID, user.Id)
	if err == nil {
		t.Fatal("expected second merge to fail")
	}
}

func TestMergeUsefulConflictKeepsTrue(t *testing.T) {
	app := testutil.NewApp(t)
	_, gOwner := testutil.MakeGuest(t, app)
	user := testutil.MakeUser(t, app, "merge2@example.com")
	uOwner := authz.Owner{Kind: authz.KindUser, ID: user.Id}
	uSvc := useful.Service{App: app, Salt: "s"}
	_, _ = uSvc.Toggle(gOwner, "e2", true)
	_, _ = uSvc.Toggle(uOwner, "e2", false)

	svc := merge.Service{App: app, Library: library.Service{App: app}, VoteSalt: "s"}
	if _, err := svc.MergeGuestIntoUser(gOwner.ID, user.Id); err != nil {
		t.Fatal(err)
	}
	got, err := uSvc.Get(uOwner, "e2")
	if err != nil || !got.Useful || got.Count != 1 {
		t.Fatalf("conflict merge should keep useful=true: %+v err=%v", got, err)
	}
}

func TestMergeUsefulNoDoubleCount(t *testing.T) {
	app := testutil.NewApp(t)
	_, gOwner := testutil.MakeGuest(t, app)
	user := testutil.MakeUser(t, app, "double@example.com")
	uOwner := authz.Owner{Kind: authz.KindUser, ID: user.Id}
	uSvc := useful.Service{App: app, Salt: "s"}
	_, _ = uSvc.Toggle(gOwner, "e1", true)
	_, _ = uSvc.Toggle(uOwner, "e1", true)
	n, err := uSvc.Count("e1")
	if err != nil || n != 2 {
		t.Fatalf("pre-merge count want 2 got %d err=%v", n, err)
	}

	svc := merge.Service{App: app, Library: library.Service{App: app}, VoteSalt: "s"}
	if _, err := svc.MergeGuestIntoUser(gOwner.ID, user.Id); err != nil {
		t.Fatal(err)
	}
	n, err = uSvc.Count("e1")
	if err != nil || n != 1 {
		t.Fatalf("post-merge count want 1 got %d err=%v", n, err)
	}
	got, err := uSvc.Get(uOwner, "e1")
	if err != nil || !got.Useful || got.Count != 1 {
		t.Fatalf("%+v err=%v", got, err)
	}
}

func TestMergeSelfcheckGuestWinsConflicts(t *testing.T) {
	app := testutil.NewApp(t)
	_, gOwner := testutil.MakeGuest(t, app)
	user := testutil.MakeUser(t, app, "sc-merge@example.com")
	uOwner := authz.Owner{Kind: authz.KindUser, ID: user.Id}
	sc := selfcheck.Service{App: app}
	_ = sc.Put(gOwner, selfcheck.Answers{"1-1": 1, "1-2": 0})
	_ = sc.Put(uOwner, selfcheck.Answers{"1-1": 0, "1-3": 1})

	svc := merge.Service{App: app, Library: library.Service{App: app}, VoteSalt: "s"}
	res, err := svc.MergeGuestIntoUser(gOwner.ID, user.Id)
	if err != nil {
		t.Fatal(err)
	}
	if res.SelfcheckMerged != 2 {
		t.Fatalf("%+v", res)
	}
	got, _ := sc.Get(uOwner)
	if len(got) != 3 || got["1-1"] != 1 || got["1-2"] != 0 || got["1-3"] != 1 {
		t.Fatalf("guest must win conflicts, keep union: %+v", got)
	}
}
