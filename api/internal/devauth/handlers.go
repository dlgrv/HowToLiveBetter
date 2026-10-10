package devauth

import (
	"net/http"

	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
)

const StubEmail = "dev@htlb.local"

// Register mounts stub login routes when enabled (HTLB_DEV=1 only).
func Register(g *router.RouterGroup[*core.RequestEvent], app core.App, enabled bool) {
	if !enabled {
		return
	}
	h := handlers{App: app}
	g.GET("/dev/status", h.status)
	g.POST("/dev/login", h.login)
}

type handlers struct {
	App core.App
}

func (h handlers) status(e *core.RequestEvent) error {
	return e.JSON(http.StatusOK, map[string]any{"enabled": true, "email": StubEmail})
}

func (h handlers) login(e *core.RequestEvent) error {
	token, err := IssueToken(h.App)
	if err != nil {
		return e.InternalServerError("dev login failed", err)
	}
	return e.JSON(http.StatusOK, map[string]any{
		"token": token,
		"email": StubEmail,
	})
}

// IssueToken creates/finds the stub user and returns a PocketBase auth JWT.
func IssueToken(app core.App) (string, error) {
	rec, err := ensureStubUser(app)
	if err != nil {
		return "", err
	}
	return rec.NewAuthToken()
}

func ensureStubUser(app core.App) (*core.Record, error) {
	if rec, err := app.FindAuthRecordByEmail("users", StubEmail); err == nil {
		return rec, nil
	}
	col, err := app.FindCollectionByNameOrId("users")
	if err != nil {
		return nil, err
	}
	was := col.PasswordAuth.Enabled
	fields := col.PasswordAuth.IdentityFields
	col.PasswordAuth.Enabled = true
	col.PasswordAuth.IdentityFields = []string{"email"}
	if err := app.Save(col); err != nil {
		return nil, err
	}
	defer func() {
		col.PasswordAuth.Enabled = was
		col.PasswordAuth.IdentityFields = fields
		_ = app.Save(col)
	}()

	rec := core.NewRecord(col)
	rec.SetEmail(StubEmail)
	rec.SetPassword("dev-stub-password-not-used")
	rec.SetVerified(true)
	if err := app.Save(rec); err != nil {
		return nil, err
	}
	return rec, nil
}
