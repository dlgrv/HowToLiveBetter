package guest

import (
	"net/http"
	"time"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
)

type Handlers struct {
	Svc Service
	Az  authz.Resolver
}

func Register(g *router.RouterGroup[*core.RequestEvent], h Handlers) {
	g.POST("/guest/session", h.createSession)
	g.POST("/guest/claim-code", h.createClaimCode)
	g.POST("/guest/claim", h.claim)
}

func (h Handlers) createSession(e *core.RequestEvent) error {
	token, exp, err := h.Svc.CreateSession()
	if err != nil {
		return e.InternalServerError("failed to create guest session", err)
	}
	return e.JSON(http.StatusOK, map[string]any{
		"token":     token,
		"expiresAt": exp.UTC().Format(time.RFC3339),
	})
}

func (h Handlers) createClaimCode(e *core.RequestEvent) error {
	owner, err := h.Az.Resolve(e)
	if err != nil || owner.Kind != authz.KindGuest {
		return e.UnauthorizedError("guest credential required", nil)
	}
	code, exp, err := h.Svc.CreateClaimCode(owner.ID)
	if err != nil {
		return e.InternalServerError("failed to create claim code", err)
	}
	return e.JSON(http.StatusOK, map[string]any{
		"code":      code,
		"expiresAt": exp.UTC().Format(time.RFC3339),
	})
}

func (h Handlers) claim(e *core.RequestEvent) error {
	var body struct {
		Code string `json:"code"`
	}
	if err := e.BindBody(&body); err != nil || body.Code == "" {
		return e.BadRequestError("code is required", nil)
	}
	token, exp, err := h.Svc.Claim(body.Code)
	if err != nil {
		return apis.NewApiError(http.StatusUnauthorized, err.Error(), nil)
	}
	return e.JSON(http.StatusOK, map[string]any{
		"token":     token,
		"expiresAt": exp.UTC().Format(time.RFC3339),
	})
}
