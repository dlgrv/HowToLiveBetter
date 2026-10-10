package app

import (
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/config"
	"github.com/dlgrv/HowToLiveBetter/api/internal/guest"
	"github.com/dlgrv/HowToLiveBetter/api/internal/library"
	"github.com/dlgrv/HowToLiveBetter/api/internal/merge"
	"github.com/dlgrv/HowToLiveBetter/api/internal/useful"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
)

// Bind wires custom routes and runtime auth settings onto the PocketBase app.
func Bind(pb *pocketbase.PocketBase, cfg config.Config) {
	pb.OnBootstrap().BindFunc(func(e *core.BootstrapEvent) error {
		if err := e.Next(); err != nil {
			return err
		}
		return applyOAuth(e.App, cfg)
	})

	pb.OnServe().BindFunc(func(e *core.ServeEvent) error {
		e.Router.Bind(apis.CORS(apis.CORSConfig{
			AllowOrigins: cfg.CORSOrigins,
			AllowMethods: []string{
				http.MethodGet, http.MethodHead, http.MethodPut,
				http.MethodPatch, http.MethodPost, http.MethodDelete, http.MethodOptions,
			},
			AllowHeaders: []string{
				"Accept", "Authorization", "Content-Type", "X-HTLB-Sync",
			},
			AllowCredentials: false,
		}))

		az := authz.Resolver{App: e.App}
		gSvc := guest.Service{App: e.App, GuestTTL: cfg.GuestTTL, ClaimTTL: cfg.ClaimTTL}
		uSvc := useful.Service{App: e.App, Salt: cfg.VoteSalt}
		lSvc := library.Service{App: e.App}
		mSvc := merge.Service{App: e.App, Library: lSvc, Salt: cfg.VoteSalt}

		g := e.Router.Group("/api/htlb/v1")
		g.GET("/health", func(re *core.RequestEvent) error {
			return re.JSON(http.StatusOK, map[string]any{
				"ok":      true,
				"version": cfg.Version,
				"time":    time.Now().UTC().Format(time.RFC3339),
			})
		})
		guest.Register(g, guest.Handlers{Svc: gSvc, Az: az})
		useful.Register(g, useful.Handlers{Svc: uSvc, Az: az})
		library.Register(g, library.Handlers{Svc: lSvc, Az: az})
		merge.Register(g, merge.Handlers{Svc: mSvc, Az: az})
		return e.Next()
	})
}

func applyOAuth(app core.App, cfg config.Config) error {
	_ = cfg
	users, err := app.FindCollectionByNameOrId("users")
	if err != nil {
		return err
	}
	lockUsersExceptOAuthCreate(users)
	users.PasswordAuth.Enabled = false

	googleID := strings.TrimSpace(os.Getenv("HTLB_OAUTH_GOOGLE_CLIENT_ID"))
	googleSecret := strings.TrimSpace(os.Getenv("HTLB_OAUTH_GOOGLE_CLIENT_SECRET"))
	githubID := strings.TrimSpace(os.Getenv("HTLB_OAUTH_GITHUB_CLIENT_ID"))
	githubSecret := strings.TrimSpace(os.Getenv("HTLB_OAUTH_GITHUB_CLIENT_SECRET"))

	providers := []core.OAuth2ProviderConfig{}
	if googleID != "" && googleSecret != "" {
		providers = append(providers, core.OAuth2ProviderConfig{
			Name:         "google",
			ClientId:     googleID,
			ClientSecret: googleSecret,
		})
	}
	if githubID != "" && githubSecret != "" {
		providers = append(providers, core.OAuth2ProviderConfig{
			Name:         "github",
			ClientId:     githubID,
			ClientSecret: githubSecret,
		})
	}
	users.OAuth2.Providers = providers
	users.OAuth2.Enabled = len(providers) > 0
	return app.Save(users)
}

// lockUsersExceptOAuthCreate keeps users CRUD locked except Create, which must
// allow OAuth signup (nil CreateRule = superuser-only → new OAuth users fail).
func lockUsersExceptOAuthCreate(c *core.Collection) {
	c.ListRule = nil
	c.ViewRule = nil
	c.UpdateRule = nil
	c.DeleteRule = nil
	c.ManageRule = nil
	oauthCreate := `@request.context = "oauth2"`
	c.CreateRule = &oauthCreate
}
