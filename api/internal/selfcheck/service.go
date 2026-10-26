package selfcheck

import (
	"encoding/json"
	"errors"
	"fmt"

	"github.com/pocketbase/dbx"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/pocketbase/pocketbase/core"
)

type Service struct {
	App core.App
}

// Answers maps entryId ("sec-n", shared across locales) to the yes/no answer
// (1 = yes, 0 = no). One record per owner; the client sends the full map.
type Answers map[string]int8

// ErrInvalid marks validation failures (→ HTTP 400).
var ErrInvalid = errors.New("invalid answers")

const maxAnswers = 2000

func ownerFilter(owner authz.Owner) (string, dbx.Params) {
	return "ownerKind = {:k} && ownerId = {:i}", dbx.Params{
		"k": string(owner.Kind),
		"i": owner.ID,
	}
}

func validate(answers Answers) error {
	if len(answers) == 0 {
		return fmt.Errorf("%w: empty", ErrInvalid)
	}
	if len(answers) > maxAnswers {
		return fmt.Errorf("%w: too many entries", ErrInvalid)
	}
	for k, v := range answers {
		if k == "" || len(k) > 120 {
			return fmt.Errorf("%w: bad entryId %q", ErrInvalid, k)
		}
		if v != 0 && v != 1 {
			return fmt.Errorf("%w: answer must be 0 or 1", ErrInvalid)
		}
	}
	return nil
}

func (s Service) Get(owner authz.Owner) (Answers, error) {
	f, p := ownerFilter(owner)
	rec, err := s.App.FindFirstRecordByFilter("selfcheck_answers", f, p)
	if err != nil {
		return Answers{}, nil
	}
	out := Answers{}
	raw := rec.GetString("answers")
	if raw == "" {
		return out, nil
	}
	if err := json.Unmarshal([]byte(raw), &out); err != nil {
		return nil, err
	}
	return out, nil
}

func (s Service) Put(owner authz.Owner, answers Answers) error {
	if err := validate(answers); err != nil {
		return err
	}
	buf, err := json.Marshal(answers)
	if err != nil {
		return err
	}
	col, err := s.App.FindCollectionByNameOrId("selfcheck_answers")
	if err != nil {
		return err
	}
	f, p := ownerFilter(owner)
	rec, err := s.App.FindFirstRecordByFilter("selfcheck_answers", f, p)
	if err != nil {
		rec = core.NewRecord(col)
		rec.Set("ownerKind", string(owner.Kind))
		rec.Set("ownerId", owner.ID)
	}
	rec.Set("answers", string(buf))
	return s.App.Save(rec)
}

// Overlay merges src over dst (src wins per key) — used by guest→user merge.
func Overlay(dst, src Answers) Answers {
	out := make(Answers, len(dst)+len(src))
	for k, v := range dst {
		out[k] = v
	}
	for k, v := range src {
		out[k] = v
	}
	return out
}
