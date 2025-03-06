import { inject, Injectable } from '@angular/core';
import { Dashboard } from '../models/dashboard.model';
import { Observable, of } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { ApiService } from '../../../core/services/api.service';
import { PaginationResponse } from '../../../shared/models/Pagination.model';
import { HttpParams } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class TeacherService {
  private apiUrl = `${environment.apiUrl}/teacher`;
  private apiService = inject(ApiService);

  getQuestionnaires(
    searchTerm: string,
    searchType: string,
    currentPage: number,
    pageSize: number,
    filterStudentCompleted: boolean,
    filterTeacherCompleted: boolean
  ): Observable<PaginationResponse<Dashboard>> {
    // Build the query params
    let params = new HttpParams()
      .set('searchTerm', searchTerm)
      .set('searchType', searchType)
      .set('currentPage', currentPage)
      .set('pageSize', pageSize)
      .set('filterStudentCompleted', filterStudentCompleted)
      .set('filterTeacherCompleted', filterTeacherCompleted);

    return this.apiService.get<PaginationResponse<Dashboard>>(
      `${this.apiUrl}/questionnaires`,
      params
    );
  }
}
