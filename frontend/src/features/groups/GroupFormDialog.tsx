import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "@/api/client";
import type { AttributeRow } from "@/components/AttributeEditor";
import { AttributeEditor } from "@/components/AttributeEditor";
import { Button, Dialog, Input } from "@/components/ui/primitives";
import type { GroupDetail } from "@/features/groups/groupsApi";
import { useGroupMutations } from "@/features/groups/useGroups";

interface GroupFormDialogProps {
  open: boolean;
  group: GroupDetail | null;
  onClose: () => void;
}

export function GroupFormDialog({ open, group, onClose }: GroupFormDialogProps) {
  const { t } = useTranslation();
  const { create, update } = useGroupMutations();
  const isEdit = group !== null;

  const [groupname, setGroupname] = useState("");
  const [checkAttributes, setCheckAttributes] = useState<AttributeRow[]>([]);
  const [replyAttributes, setReplyAttributes] = useState<AttributeRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    setError(null);
    setGroupname(group?.groupname ?? "");
    setCheckAttributes(group?.check_attributes ?? []);
    setReplyAttributes(group?.reply_attributes ?? []);
  }, [open, group]);

  const onSubmit = async () => {
    setError(null);
    setIsSaving(true);
    try {
      if (isEdit) {
        await update.mutateAsync({
          groupname: group.groupname,
          payload: { check_attributes: checkAttributes, reply_attributes: replyAttributes },
        });
      } else {
        await create.mutateAsync({
          groupname,
          check_attributes: checkAttributes,
          reply_attributes: replyAttributes,
        });
      }
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.unknownError"));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      title={isEdit ? t("groups.form.editTitle") : t("groups.form.createTitle")}
      onClose={onClose}
    >
      <div className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="groupname" className="text-sm font-medium">
            {t("groups.fields.groupname")}
          </label>
          <Input
            id="groupname"
            disabled={isEdit}
            value={groupname}
            onChange={(event) => setGroupname(event.target.value)}
            placeholder="pppoe-standard"
          />
        </div>

        <AttributeEditor
          label={t("groups.fields.checkAttributes")}
          rows={checkAttributes}
          onChange={setCheckAttributes}
        />
        <AttributeEditor
          label={t("groups.fields.replyAttributes")}
          rows={replyAttributes}
          onChange={setReplyAttributes}
        />

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            type="button"
            disabled={isSaving || (!isEdit && groupname.trim() === "")}
            onClick={() => void onSubmit()}
          >
            {t("common.save")}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
