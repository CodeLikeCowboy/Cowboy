import APIClient from "../api/APIClient";
import { fetchConfig } from "../config";
import { UnitTest, UnitTestDecision, CompareURLResponse } from "../types/API";


async function getTestResults(sessionId: string): Promise<UnitTest[]> {
    const api = new APIClient(await fetchConfig());
    const test_results = await api.get(`/test-gen/results/${sessionId}`);

    return test_results as UnitTest[];
};

async function submitTestResults(sessionId: string, decisions: UnitTestDecision[]): Promise<CompareURLResponse> {
    const api = new APIClient(await fetchConfig());

    const res = await api.post(`/test-gen/results/decide/${sessionId}`, {"user_decision": decisions});
    return res as CompareURLResponse;
}


export {getTestResults, submitTestResults};