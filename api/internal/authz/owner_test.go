package authz_test

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
	"github.com/pocketbase/pocketbase/core"
)

func TestResolveUnauthorized(t *testing.T) {
	app := testutil.NewApp(t)
	e := &core.RequestEvent{App: app}
	e.Request = httptest.NewRequest(http.MethodGet, "/", nil)
	_, err := authz.Resolver{App: app}.Resolve(e)
	if !errors.Is(err, authz.ErrUnauthorized) {
		t.Fatalf("got %v", err)
	}
}

func TestResolveGuest(t *testing.T) {
	app := testutil.NewApp(t)
	token, owner := testutil.MakeGuest(t, app)
	e := &core.RequestEvent{App: app}
	e.Request = httptest.NewRequest(http.MethodGet, "/", nil)
	e.Request.Header.Set(authz.HeaderSync, token)
	got, err := authz.Resolver{App: app}.Resolve(e)
	if err != nil {
		t.Fatal(err)
	}
	if got != owner {
		t.Fatalf("got %+v want %+v", got, owner)
	}
}

func TestResolveExpiredGuest(t *testing.T) {
	app := testutil.NewApp(t)
	token, owner := testutil.MakeGuest(t, app)
	testutil.ExpireGuest(t, app, owner.ID)
	e := &core.RequestEvent{App: app}
	e.Request = httptest.NewRequest(http.MethodGet, "/", nil)
	e.Request.Header.Set(authz.HeaderSync, token)
	_, err := authz.Resolver{App: app}.Resolve(e)
	if !errors.Is(err, authz.ErrUnauthorized) {
		t.Fatalf("got %v", err)
	}
}

func TestUserAuthTakesPriority(t *testing.T) {
	app := testutil.NewApp(t)
	token, _ := testutil.MakeGuest(t, app)
	user := testutil.MakeUser(t, app, "u@example.com")
	e := &core.RequestEvent{App: app, Auth: user}
	e.Request = httptest.NewRequest(http.MethodGet, "/", nil)
	e.Request.Header.Set(authz.HeaderSync, token)
	got, err := authz.Resolver{App: app}.Resolve(e)
	if err != nil {
		t.Fatal(err)
	}
	if got.Kind != authz.KindUser || got.ID != user.Id {
		t.Fatalf("got %+v", got)
	}
}
