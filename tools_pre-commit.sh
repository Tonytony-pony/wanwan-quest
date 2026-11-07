#!/bin/sh
# ひみつの もじれつを、うっかり コミットしない ための みはり（Git の pre-commit フック）。
#
# いれかた（このPCで 1かい だけ。.git/hooks は Git に はいらない ので、PCごとに ひつよう）:
#   cp tools_pre-commit.sh .git/hooks/pre-commit
#
# 2026-10 に Discord の Webhook URL を こうかい リポジトリに コミットして、
# じどうスキャナに ぬすまれ のっとられた。おなじ ことを くりかえさない ため。
# リポジトリは PUBLIC。コミットは けしても Git りれきに のこり、だれでも よめる。

# しゅつりょくの うけてが とちゅうで とじても（SIGPIPE）、かならず「とめる」で おわる ように する。
# （これが ないと、フックが しんで コミットが とおって しまう）
trap '' PIPE

# 1) ついかされる 行（+ の 行）に ひみつらしい もじれつが ないか
PATTERN='discord(app)?\.com/api/webhooks/[0-9]{6,}/[A-Za-z0-9_-]{20,}'
PATTERN="$PATTERN|ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|ghu_[A-Za-z0-9]{30,}|ghs_[A-Za-z0-9]{30,}|ghr_[A-Za-z0-9]{30,}"
PATTERN="$PATTERN|github_pat_[A-Za-z0-9_]{30,}|AIza[0-9A-Za-z_-]{35}|AKIA[0-9A-Z]{16}"
PATTERN="$PATTERN|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[abprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{32,}"

HITS=$(git diff --cached -U0 --no-color | grep -E '^\+' | grep -vE '^\+\+\+' | grep -E "$PATTERN" | cut -c1-90)
if [ -n "$HITS" ]; then
  {
    echo ""
    echo "✋ コミットを とめました：ひみつらしい もじれつが はいって います。"
    echo "$HITS" | sed 's/^/     /'
    echo ""
    echo "   この リポジトリは こうかい です。コミットすると だれでも よめて、じどうで ぬすまれます。"
    echo "   Webhook URL・トークンは コードに かかず、たんまつの せってい（おうちの人へ）にだけ いれる。"
    echo "   ほんとうに モンダイなければ:  git commit --no-verify"
  } >&2 || true
  exit 1
fi

# 2) ひみつの はいりやすい ファイルの なまえ
BADFILES=$(git diff --cached --name-only --diff-filter=AM | grep -E '(^|/)(\.env(\..*)?|webhook-local\.js|.*\.pem|.*\.key|セーブ控え/.*)$')
if [ -n "$BADFILES" ]; then
  {
    echo ""
    echo "✋ コミットを とめました：ひみつ／こじんじょうほうの ファイルが はいって います。"
    echo "$BADFILES" | sed 's/^/     /'
    echo "   ほんとうに モンダイなければ:  git commit --no-verify"
  } >&2 || true
  exit 1
fi
exit 0
