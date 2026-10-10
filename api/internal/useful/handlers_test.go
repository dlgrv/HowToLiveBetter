package useful_test

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
	"github.com/dlgrv/HowToLiveBetter/api/internal/useful"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
)

func usefulHandlers(app core.App) useful.Handlers {
	return useful.Handlers{
		Svc: useful.Service{App: app, Salt: "test-salt"},
		Az:  authz.Resolver{App: app},
	}
}

func newUsefulEvent(app core.App, method, target string, body []byte) (*core.RequestEvent, *httptest.ResponseRecorder) {
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(method, target, bytes.NewReader(body))
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	e := &core.RequestEvent{App: app}
	e.Request = req
	e.Response = rec
	return e, rec
}

func apiStatus(err error) int {
	if err == nil {
		return http.StatusOK
	}
	var ae *router.ApiError
	if ok := asAPIError(err, &ae); ok {
		return ae.Status
	}
	return 0
}

func asAPIError(err error, out **router.ApiError) bool {
	var ae *router.ApiError
	if !errors.As(err, &ae) {
		return false
	}
	*out = ae
	return true
}

func TestPostGuestUnauthorized(t *testing.T) {
	app := testutil.NewApp(t)
	token, _ := testutil.MakeGuest(t, app)
	h := usefulHandlers(app)
	body, _ := json.Marshal(map[string]any{"entryId": "e1", "useful": true})
	e, _ := newUsefulEvent(app, http.MethodPost, "/useful", body)
	e.Request.Header.Set(authz.HeaderSync, token)
	err := h.Post(e)
	if apiStatus(err) != http.StatusUnauthorized {
		t.Fatalf("want 401 got %v (%v)", apiStatus(err), err)
	}
}

func TestPostUserOK(t *testing.T) {
	app := testutil.NewApp(t)
	user := testutil.MakeUser(t, app, "voter@example.com")
	h := usefulHandlers(app)
	body, _ := json.Marshal(map[string]any{"entryId": "e1", "useful": true})
	e, rec := newUsefulEvent(app, http.MethodPost, "/useful", body)
	e.Auth = user
	err := h.Post(e)
	if err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Fatalf("status %d body %s", rec.Code, rec.Body.String())
	}
	var res useful.VoteResult
	if err := json.Unmarshal(rec.Body.Bytes(), &res); err != nil {
		t.Fatal(err)
	}
	if !res.Useful || res.Count != 1 {
		t.Fatalf("%+v", res)
	}
}

func TestGetAnonymousCountOnly(t *testing.T) {
	app := testutil.NewApp(t)
	user := testutil.MakeUser(t, app, "anon-get@example.com")
	svc := useful.Service{App: app, Salt: "test-salt"}
	_, _ = svc.Toggle(authz.Owner{Kind: authz.KindUser, ID: user.Id}, "e1", true)

	h := usefulHandlers(app)
	e, rec := newUsefulEvent(app, http.MethodGet, "/useful?entryIds=e1", nil)
	if err := h.Get(e); err != nil {
		t.Fatal(err)
	}
	var out struct {
		Items []map[string]any `json:"items"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatal(err)
	}
	if len(out.Items) != 1 {
		t.Fatalf("%+v", out)
	}
	if out.Items[0]["count"] != float64(1) {
		t.Fatalf("count %+v", out.Items[0])
	}
	if _, has := out.Items[0]["useful"]; has {
		t.Fatalf("anonymous GET must omit useful: %+v", out.Items[0])
	}
}

func TestGetGuestOmitsUseful(t *testing.T) {
	app := testutil.NewApp(t)
	token, gOwner := testutil.MakeGuest(t, app)
	svc := useful.Service{App: app, Salt: "test-salt"}
	_, _ = svc.Toggle(gOwner, "e1", true)

	h := usefulHandlers(app)
	e, rec := newUsefulEvent(app, http.MethodGet, "/useful?entryIds=e1", nil)
	e.Request.Header.Set(authz.HeaderSync, token)
	if err := h.Get(e); err != nil {
		t.Fatal(err)
	}
	var out struct {
		Items []map[string]any `json:"items"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatal(err)
	}
	if _, has := out.Items[0]["useful"]; has {
		t.Fatalf("guest GET must omit useful: %+v", out.Items[0])
	}
}

func TestGetUserIncludesUseful(t *testing.T) {
	app := testutil.NewApp(t)
	user := testutil.MakeUser(t, app, "user-get@example.com")
	svc := useful.Service{App: app, Salt: "test-salt"}
	_, _ = svc.Toggle(authz.Owner{Kind: authz.KindUser, ID: user.Id}, "e1", true)

	h := usefulHandlers(app)
	e, rec := newUsefulEvent(app, http.MethodGet, "/useful?entryIds=e1", nil)
	e.Auth = user
	if err := h.Get(e); err != nil {
		t.Fatal(err)
	}
	var out struct {
		Items []map[string]any `json:"items"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatal(err)
	}
	u, ok := out.Items[0]["useful"].(bool)
	if !ok || !u {
		t.Fatalf("want useful=true got %+v", out.Items[0])
	}
}

func TestMineGuestUnauthorized(t *testing.T) {
	app := testutil.NewApp(t)
	token, _ := testutil.MakeGuest(t, app)
	h := usefulHandlers(app)
	e, _ := newUsefulEvent(app, http.MethodGet, "/useful/mine", nil)
	e.Request.Header.Set(authz.HeaderSync, token)
	err := h.Mine(e)
	if apiStatus(err) != http.StatusUnauthorized {
		t.Fatalf("want 401 got %v (%v)", apiStatus(err), err)
	}
}

func TestMineUserListsUsefulOnly(t *testing.T) {
	app := testutil.NewApp(t)
	user := testutil.MakeUser(t, app, "mine@example.com")
	owner := authz.Owner{Kind: authz.KindUser, ID: user.Id}
	svc := useful.Service{App: app, Salt: "test-salt"}
	_, _ = svc.Toggle(owner, "2-1", true)
	_, _ = svc.Toggle(owner, "1-3", true)
	_, _ = svc.Toggle(owner, "1-2", true)
	_, _ = svc.Toggle(owner, "1-2", false)

	h := usefulHandlers(app)
	e, rec := newUsefulEvent(app, http.MethodGet, "/useful/mine", nil)
	e.Auth = user
	if err := h.Mine(e); err != nil {
		t.Fatal(err)
	}
	var out struct {
		Items []struct {
			EntryID string `json:"entryId"`
		} `json:"items"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatal(err)
	}
	if len(out.Items) != 2 {
		t.Fatalf("want 2 got %+v", out.Items)
	}
	if out.Items[0].EntryID != "1-3" || out.Items[1].EntryID != "2-1" {
		t.Fatalf("want sorted [1-3, 2-1] got %+v", out.Items)
	}
}
