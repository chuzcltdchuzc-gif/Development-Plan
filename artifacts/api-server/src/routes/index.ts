import { Router, type IRouter } from "express";
import healthRouter from "./health";
import parcelsRouter from "./parcels";
import evidenceRouter from "./evidence";
import dashboardRouter from "./dashboard";

const router: IRouter = Router();

router.use(healthRouter);
router.use(dashboardRouter);
router.use(parcelsRouter);
router.use(evidenceRouter);

export default router;
