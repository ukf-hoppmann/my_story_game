import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useCreatePromptOptionMutation } from "../../api/apiSlice";
import { Button } from "../../components/Button/Button";
import { ErrorBanner } from "../../components/ErrorBanner/ErrorBanner";

/** Same shape the backend enforces: a short lowercase slug. */
const OPTION_ID = /^[a-z][a-z0-9_]{1,39}$/;

/** Adds a selectable option to one category. The id becomes part of the
 *  key (`<category>/<id>`) and cannot change afterwards. */
export function NewOptionForm({ category, onClose }: { category: string; onClose: () => void }) {
  const { t } = useTranslation();
  const [optionId, setOptionId] = useState("");
  const [text, setText] = useState("");
  const [create, state] = useCreatePromptOptionMutation();

  const valid = OPTION_ID.test(optionId) && text.trim() !== "";

  const submit = async () => {
    const result = await create({ category, option_id: optionId, text });
    if (!("error" in result)) {
      onClose();
    }
  };

  return (
    <div className="settings-new-option">
      <label className="settings-field">
        <span>{t("settings.newOption.id")}</span>
        <input
          value={optionId}
          onChange={(event) => setOptionId(event.target.value)}
          placeholder="melancholic"
          maxLength={40}
        />
      </label>
      <p className="settings-muted">{t("settings.newOption.idHint")}</p>
      <label className="settings-field">
        <span>{t("settings.newOption.text")}</span>
        <textarea
          className="settings-textarea"
          rows={4}
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
      </label>
      <ErrorBanner error={state.error} fallbackKey="settings.newOption.error" className="settings-error" />
      <div className="settings-entry-actions">
        <Button disabled={!valid || state.isLoading} onClick={() => void submit()}>
          {t("settings.newOption.create")}
        </Button>
        <Button variant="ghost" onClick={onClose}>
          {t("settings.newOption.cancel")}
        </Button>
      </div>
    </div>
  );
}
