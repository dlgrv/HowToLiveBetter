package merge

import (
	"net/http"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
)

type Handlers struct {
	Svc Service
	Az  authz.Resolver
}

func Register(g *router.RouterGroup[*core.RequestEvent], h Handlers) {
	g.POST("/merge", h.merge)
}

func (h Handlers) merge(e *core.RequestEvent) error {
	if e.Auth == nil {
		return e.UnauthorizedError("user login required", nil)
	}
	raw := e.Request.Header.Get(authz.HeaderSync)
	if raw == "" {
		return e.BadRequestError("X-HTLB-Sync required for merge", nil)
	}
	hash := authz.HashToken(raw)
	guest, err := h.Svc.App.FindFirstRecordByFilter(
		"guest_sessions",
		"tokenHash = {:h} && status = 'active'",
		dbx.Params{"h": hash},
	)
	if err != nil {
		return e.UnauthorizedError("invalid guest credential", nil)
	}
	res, err := h.Svc.MergeGuestIntoUser(guest.Id, e.Auth.Id)
	if err != nil {
		return e.BadRequestError(err.Error(), nil)
	}
	return e.JSON(http.StatusOK, res)
}
