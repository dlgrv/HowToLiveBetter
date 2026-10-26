package selfcheck

import (
	"errors"
	"net/http"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
)

type Handlers struct {
	Svc Service
	Az  authz.Resolver
}

func Register(g *router.RouterGroup[*core.RequestEvent], h Handlers) {
	g.GET("/selfcheck", h.Get)
	g.PUT("/selfcheck", h.Put)
}

func (h Handlers) requireOwner(e *core.RequestEvent) (authz.Owner, error) {
	owner, err := h.Az.Resolve(e)
	if err != nil {
		return owner, e.UnauthorizedError("credential required", nil)
	}
	return owner, nil
}

func (h Handlers) Get(e *core.RequestEvent) error {
	owner, err := h.requireOwner(e)
	if err != nil {
		return err
	}
	answers, err := h.Svc.Get(owner)
	if err != nil {
		return e.InternalServerError("get failed", err)
	}
	return e.JSON(http.StatusOK, map[string]any{"answers": answers})
}

func (h Handlers) Put(e *core.RequestEvent) error {
	owner, err := h.requireOwner(e)
	if err != nil {
		return err
	}
	var body struct {
		Answers Answers `json:"answers"`
	}
	if err := e.BindBody(&body); err != nil {
		return e.BadRequestError("answers required", nil)
	}
	if err := h.Svc.Put(owner, body.Answers); err != nil {
		if errors.Is(err, ErrInvalid) {
			return e.BadRequestError(err.Error(), nil)
		}
		return e.InternalServerError("save failed", err)
	}
	return e.JSON(http.StatusOK, map[string]any{"ok": true})
}
