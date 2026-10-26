package selfcheck_test

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/selfcheck"
	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
	"github.com/pocketbase/pocketbase/core"
)

func handlers(app core.App) selfcheck.Handlers {
	return selfcheck.Handlers{
		Svc: selfcheck.Service{App: app},
		Az:  authz.Resolver{App: app},
	}
}

func event(app core.App, method, target string, body []byte, token string) (*core.RequestEvent, *httptest.ResponseRecorder) {
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(method, target, bytes.NewReader(body))
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if token != "" {
		req.Header.Set("X-HTLB-Sync", token)
	}
	e := &core.RequestEvent{App: app}
	e.Request = req
	e.Response = rec
	return e, rec
}

func TestGetRequiresAuth(t *testing.T) {
	app := testutil.NewApp(t)
	h := handlers(app)
	e, _ := event(app, "GET", "/api/htlb/v1/selfcheck", nil, "")
	if err := h.Get(e); err == nil {
		t.Fatal("expected unauthorized")
	}
}

func TestPutAndGetWithGuestToken(t *testing.T) {
	app := testutil.NewApp(t)
	token, _ := testutil.MakeGuest(t, app)
	h := handlers(app)

	body, _ := json.Marshal(map[string]any{"answers": map[string]int8{"4-2": 1, "5-1": 0}})
	pe, _ := event(app, "PUT", "/api/htlb/v1/selfcheck", body, token)
	if err := h.Put(pe); err != nil {
		t.Fatal(err)
	}

	e, rec := event(app, "GET", "/api/htlb/v1/selfcheck", nil, token)
	if err := h.Get(e); err != nil {
		t.Fatal(err)
	}
	var out struct {
		Answers map[string]int8 `json:"answers"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatal(err)
	}
	if len(out.Answers) != 2 || out.Answers["4-2"] != 1 || out.Answers["5-1"] != 0 {
		t.Fatalf("got %s", rec.Body.String())
	}
}

func TestPutRejectsInvalidBody(t *testing.T) {
	app := testutil.NewApp(t)
	token, _ := testutil.MakeGuest(t, app)
	h := handlers(app)

	cases := [][]byte{
		[]byte(`{"answers":{}}`),
		[]byte(`{"answers":{"1-1":7}}`),
		[]byte(`not json`),
	}
	for i, body := range cases {
		pe, _ := event(app, "PUT", "/api/htlb/v1/selfcheck", body, token)
		if err := h.Put(pe); err == nil {
			t.Fatalf("case %d: expected error", i)
		}
	}
}
