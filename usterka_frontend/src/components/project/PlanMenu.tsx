import { createPortal } from 'react-dom';
import { errorMessage } from 'src/service/http';
import { PlanService } from 'src/service/plan';
import { useProjectStore } from 'src/stores/projectStore';
import { dialog, toast } from 'src/stores/uiStore';
import type { Plan } from 'src/types/api';

export default function PlanMenu({ plan, onClose }: { plan: Plan; onClose: () => void }) {
  const { upsertPlan, removePlan, refreshProject } = useProjectStore();
  const rename = async () => {
    onClose();
    const n = await dialog({ title: 'Nazwa planu', input: plan.name, okLabel: 'Zapisz' });
    if (!n) return;
    try {
      upsertPlan(await PlanService.rename(plan.id, n));
    } catch (e) {
      toast(errorMessage(e));
    }
  };
  const remove = async () => {
    onClose();
    const ok = await dialog({ title: 'Usunąć plan?', text: 'Razem z planem usunięte zostaną zaznaczone na nim usterki i ich zdjęcia.', okLabel: 'Usuń plan', danger: true });
    if (!ok) return;
    try {
      await PlanService.remove(plan.id);
      removePlan(plan.id);
      refreshProject();
      toast('Plan usunięty');
    } catch (e) {
      toast(errorMessage(e));
    }
  };
  return createPortal(
    <div className="modal-back" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <h3>{plan.name}</h3>
        <div style={{ display: 'grid', gap: 8 }}>
          <button className="btn" onClick={rename}>Zmień nazwę</button>
          <button className="btn danger" onClick={remove}>Usuń plan</button>
          <button className="btn" onClick={onClose}>Anuluj</button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
